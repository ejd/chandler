include ../../Makefile.inc

DLLS_DIR=libs

ifeq ($(SNAP),debug)

DLLS=$(DLLS_DIR)/msvcp71d.dll $(DLLS_DIR)/msvcr71d.dll $(DLLS_DIR)/msvcrtd.dll

build:	winlaunch/chandlerDebug.exe

winlaunch/chandlerDebug.exe: winlaunch/winlaunch.cpp
	devenv.com winlaunch/winlaunch.sln /build $(SNAP)
	cp winlaunch/$(Snap)/chandlerDebug.exe $(BUILD_ROOT)
	cp $(DLLS) $(BUILD_ROOT)/$(SNAP)/bin

else

DLLS=$(DLLS_DIR)/msvcp71.dll $(DLLS_DIR)/msvcr71.dll

build:	winlaunch/chandler.exe

winlaunch/chandler.exe: winlaunch/winlaunch.cpp
	devenv.com winlaunch/winlaunch.sln /build $(SNAP)
	cp winlaunch/$(Snap)/chandler.exe $(BUILD_ROOT)
	cp $(DLLS) $(BUILD_ROOT)/$(SNAP)/bin

endif

clean:
	devenv.com winlaunch/winlaunch.sln /clean $(SNAP)

