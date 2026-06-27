// uaf_trigger.c - Userspace trigger for crash_uaf module
// Compile: gcc -static -o uaf_trigger uaf_trigger.c
// Runs inside QEMU initramfs, invokes ioctl sequence 0->1->2->3 to trigger UAF

#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <stdio.h>

#define UAF_IOC_TRIGGER _IOW('U', 1, unsigned long)

int main(void)
{
	int fd = open("/dev/crash_uaf", O_RDWR);
	unsigned long mode;
	int i;

	if (fd < 0) {
		perror("open /dev/crash_uaf");
		return 1;
	}

	mode = 0; ioctl(fd, UAF_IOC_TRIGGER, &mode);  // create
	mode = 1; ioctl(fd, UAF_IOC_TRIGGER, &mode);  // leak ref
	mode = 2; ioctl(fd, UAF_IOC_TRIGGER, &mode);  // free
	mode = 3; ioctl(fd, UAF_IOC_TRIGGER, &mode);  // UAF

	// should not reach here if KASAN panics
	close(fd);
	return 0;
}
