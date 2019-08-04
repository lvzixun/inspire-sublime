
mingw: inspire
	wget http://www.lua.org/ftp/lua-5.3.5.tar.gz
	tar -xvf lua-5.3.5.tar.gz
	make lua "LUA_PLATFORM = mingw"
	cp lua-5.3.5/src/lua.exe tools/windows/
	cp lua-5.3.5/src/lua53.dll tools/windows/
	make tools/windows/line.dll
	make update

inspire:
	rm -rf inspire-complete
	git clone git@github.com:lvzixun/inspire-complete.git

update:
	cd inspire-complete && git pull
	cp inspire-complete/core.lua ./
	cp inspire-complete/inspire.lua ./

tools/windows/line.dll: inspire-complete/line.c
	cc -g -O2 -Wall -shared -o $@ $^ -Iinspire-complete/ -Ilua-5.3.5/src -Llua-5.3.5/src -llua53

tools/macosx/line.so: inspire-complete/line.c
	clang -g -Wall -O2 -undefined dynamic_lookup -shared -o $@  $^ -Iinspire-complete/ -Ilua-5.3.5/src

lua:
	cd lua-5.3.5 && make mingw $(LUA_PLATFORM)