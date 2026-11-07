CC = cc
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror $(shell pkg-config --cflags dvdread)
LDLIBS = $(shell pkg-config --libs dvdread)
ifneq ($(shell uname -s),Darwin)
CFLAGS += $(shell pkg-config --cflags openssl)
LDLIBS += $(shell pkg-config --libs openssl)
endif
DVDNAV_ARCHIVE ?= ../../analysis/libdvdnav-7.0.0.tar.xz

.PHONY: all clean test trace
all: build/inspect_ifo build/inspect_nav

build:
	mkdir -p $@

build/inspect_ifo: inspect_ifo.c fingerprint.h | build
	$(CC) $(CFLAGS) $< -o $@ $(LDLIBS)

build/inspect_nav: inspect_nav.c | build
	$(CC) $(CFLAGS) $< -o $@ $(LDLIBS)

trace: build/trace_game

build/trace_game: trace_game.c fingerprint.h build_trace.py $(DVDNAV_ARCHIVE) | build
	python3 build_trace.py $(DVDNAV_ARCHIVE)

test: all trace
	cd ../.. && python3 -m unittest discover -s tests/dvd -v

clean:
	rm -rf build
