# -*- coding: utf-8 -*-

import threading
import re
import os
import sublime, sublime_plugin
from subprocess import Popen, PIPE, STDOUT
import subprocess


def char2type(char):
	if re.match(r'^[a-zA-Z_]+$', char):
		return 'A'
	elif re.match(r'\s+$', char):
		return 'S'
	else:
		return 'U'



def get_startup_info(platform):
	if platform == "windows":
		info = subprocess.STARTUPINFO()
		info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
		return info
	else:
		return None


class InspireComplete(object):
	def __init__(self):
		work_dir = os.path.dirname(os.path.realpath(__file__))
		platform = sublime.platform()
		lua_dir = work_dir
		lib_dir = os.path.join(work_dir, "tools", platform)
		lua_exe = os.path.join(work_dir, "tools", platform, "lua")
		inspire_lua =  os.path.join(lua_dir, "inspire.lua")
		if platform == "osx":
			subprocess.call(["chmod", "+x", lua_exe])
		self._inspire_server = Popen([lua_exe, inspire_lua, platform, lua_dir, lib_dir], 
			stdout=PIPE, stdin=PIPE, stderr=PIPE, 
			startupinfo=get_startup_info(sublime.platform()))
		def check_servier():
			poll = self._inspire_server.poll()
			if poll != None:
				err = self._inspire_server.stderr.readline()
				print("self._inspire_server", self._inspire_server, "poll:", poll, "err", err)
				self._inspire_server.terminate()
		sublime.set_timeout(check_servier, 400)

	def _write_line(self, l):
		l = bytes(l, 'utf-8')
		self._inspire_server.stdin.write(l)
		self._inspire_server.stdin.write(b'\n')

	def _flush(self):
		self._inspire_server.stdin.flush()

	def _write_data(self, data):
		data = bytes(data, 'utf-8')
		size = len(data)
		s = "%d\n" % (size)
		sz = bytes(s, 'UTF-8')
		self._inspire_server.stdin.write(sz)
		self._inspire_server.stdin.write(data)

	def _read_line(self):
		data = self._inspire_server.stdout.readline()
		data = str(data, "UTF-8")
		data = data.replace("\r", "")
		data = data.replace("\n", "")
		return data

	def complete_at(self, filename, source, row, col):
		self._write_line(filename)
		loc = "%d %d" % (row, col)
		self._write_line(loc)
		self._write_data(source)
		self._flush()

		result = []
		count = int(self._read_line())
		for i in range(count):
			l = self._read_line()
			result.append(l)
		return result


class InspirListener(sublime_plugin.EventListener):
	def __init__(self):
		self.inspire_complete = InspireComplete()
		self.complete = False
		self.do_complete_thread = False
		self.complete_result = False
		self.last_modify_file = False
		self.last_modify_point = False
		self.last_modify_line = False


	def check_need_completion(self, view):
		file_name = view.file_name()
		suffix = file_name and file_name.split(".")[-1]
		if not suffix or suffix == "" or suffix == "log":
			return False

		point = view.sel()[0].begin() - 1
		b = True
		cur_line = view.substr(view.line(point))
		if file_name == self.last_modify_file:
			if self.last_modify_point == point:
				b = False
			else:
				rcl = cur_line[::-1]
				rll = self.last_modify_line[::-1]
				s1 = rcl
				s2 = rll
				if len(s1) < len(s2):
					s1 = rll
					s2 = rcl
				if len(s2)>0 and s1.find(s2) == 0:
					b = False

		self.last_modify_file = file_name
		self.last_modify_point = point
		self.last_modify_line = cur_line

		if point < 0 or not b:
			return False

		cur_char = view.substr(point)
		ct = char2type(cur_char)
		prev_char = view.substr(point-1)
		pt = char2type(prev_char)
		# print("cur_char", cur_char)
		if cur_char != '\n' and ct != pt and ct != 'U':
			return True
		else:
			return False

	def on_modified(self, view):
		b = self.check_need_completion(view)
		if b:
			self.per_complete()

	def show_complete(self):
		self.complete = True
		sublime.active_window().run_command("auto_complete",
		{
			'disable_auto_insert': True,
			'api_completions_only': False,
			'next_competion_if_showing': False
		})
		self.complete = False


	def per_complete(self):
		sublime.active_window().run_command("hide_auto_complete")
		sublime.set_timeout(lambda :self.show_complete(), 0)


	def on_query_completions(self, view, prefix, locations):
		if not self.complete:
			return None
			
		flag = sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS		
		thread_prepare = not self.do_complete_thread or not self.do_complete_thread.is_alive()
		if not thread_prepare:
			print("inspire complete busy.")
			return ([], flag)

		if self.complete_result:
			ret = self.complete_result
			self.complete_result = False
			return ret

		def do_complete():
			row, col = view.rowcol(locations[0])
			row += 1
			source = view.substr(sublime.Region(0, view.size()))
			file_name = view.file_name()
			result = self.inspire_complete.complete_at(file_name, source, row, col)
			# print("prefix", prefix, locations)
			print(result) 

			if len(result)>0:
				ret = []
				for v in result:
					entry = ("%s\tinspire"%(v), v)
					ret.append(entry)
				self.complete_result = (ret, flag)
				self.per_complete()
			
		self.do_complete_thread = threading.Thread(target=do_complete)
		self.do_complete_thread.start()
		return ([], flag)
