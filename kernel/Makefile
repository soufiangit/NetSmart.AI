# SKMA-FON Kernel Module Makefile
# Author: Soufian Carson

obj-m += monitoring_module.o

KDIR := /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean

install: all
	sudo insmod monitoring_module.ko

uninstall:
	sudo rmmod monitoring_module

reload: uninstall install

test:
	@echo "Testing kernel module..."
	@if [ -f /proc/optifiber/myinfo ]; then \
		echo "✓ Proc entry exists"; \
		cat /proc/optifiber/myinfo | head -20; \
	else \
		echo "✗ Proc entry not found"; \
	fi

.PHONY: all clean install uninstall reload test