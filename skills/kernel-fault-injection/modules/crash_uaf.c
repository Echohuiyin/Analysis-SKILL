// crash_uaf.c - Use-after-free via kref reference count leak
// Triggers KASAN UAF report by freeing object while stale pointer still held
//
// Root cause narrative: a code path does kref_get() without a matching kref_put()
// (refcount leak). When the object is later torn down via the "correct" number of
// kref_put() calls, the actual refcount is higher than expected, so callers that
// kept a stale pointer believe the object is alive — but a buggy cleanup path
// calls kfree() directly (bypassing kref), leaving stale pointers dangling.
// KASAN catches the subsequent access through the stale pointer.

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/miscdevice.h>
#include <linux/fs.h>
#include <linux/kref.h>
#include <linux/slab.h>
#include <linux/uaccess.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Analysis-SKILL");
MODULE_DESCRIPTION("Fault injection: use-after-free via kref refcount leak");

struct uaf_object {
	struct kref refcnt;
	char data[64];
};

static struct uaf_object *obj;
static struct uaf_object *stale;  // stale pointer kept across free

#define UAF_IOC_TRIGGER  _IOW('U', 1, unsigned long)

static long uaf_ioctl(struct file *f, unsigned int cmd, unsigned long arg)
{
	unsigned long mode;

	if (cmd != UAF_IOC_TRIGGER)
		return -ENOTTY;
	if (copy_from_user(&mode, (void __user *)arg, sizeof(mode)))
		return -EFAULT;

	switch (mode) {
	case 0:  // create object, init kref to 1, keep stale pointer
		if (obj)
			return -EBUSY;
		obj = kzalloc(sizeof(*obj), GFP_KERNEL);
		if (!obj)
			return -ENOMEM;
		kref_init(&obj->refcnt);  // count = 1
		stale = obj;              // another code path keeps a pointer
		break;
	case 1:  // refcount leak: kref_get without matching kref_put
		if (!obj)
			return -EINVAL;
		kref_get(&obj->refcnt);  // count = 2 (leaked +1)
		break;
	case 2:  // "cleanup" path: one kref_put. count = 1 (not 0, BUT we also
		// have a buggy path that calls kfree directly when refcount > 0
		// because the developer assumed the get was balanced).
		// To reliably trigger UAF: explicitly kfree here (simulating the
		// buggy cleanup), regardless of refcount.
		if (!obj)
			return -EINVAL;
		kfree(obj);  // buggy: direct kfree bypassing kref, stale still points
		obj = NULL;
		break;
	case 3:  // UAF: write through stale pointer -> KASAN catches
		if (!stale)
			return -EINVAL;
		memset(stale->data, 'X', sizeof(stale->data));  // KASAN: use-after-free
		break;
	}
	return 0;
}

static const struct file_operations uaf_fops = {
	.owner = THIS_MODULE,
	.unlocked_ioctl = uaf_ioctl,
};

static struct miscdevice uaf_dev = {
	.minor = MISC_DYNAMIC_MINOR,
	.name  = "crash_uaf",
	.fops  = &uaf_fops,
};

static int __init crash_uaf_init(void)
{
	pr_info("=== UAF (kref refcount leak) Test ===\n");
	pr_info("Load module, then run uaf_trigger to invoke ioctl sequence\n");
	return misc_register(&uaf_dev);
}

static void __exit crash_uaf_exit(void)
{
	misc_deregister(&uaf_dev);
}

module_init(crash_uaf_init);
module_exit(crash_uaf_exit);
