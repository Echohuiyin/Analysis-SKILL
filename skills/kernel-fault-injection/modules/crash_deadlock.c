// crash_deadlock.c - Mutex ABBA deadlock fault injection
// Triggers hung task via mutex deadlock

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/mutex.h>
#include <linux/kthread.h>
#include <linux/delay.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Analysis-SKILL");
MODULE_DESCRIPTION("Fault injection: Mutex ABBA deadlock");

static DEFINE_MUTEX(mutex_a);
static DEFINE_MUTEX(mutex_b);

static struct task_struct *thread1;
static struct task_struct *thread2;

// Thread 1: lock A -> try lock B (ABBA order)
static int thread1_fn(void *data)
{
	printk(KERN_INFO "Thread 1: trying to lock A\n");
	mutex_lock(&mutex_a);
	printk(KERN_INFO "Thread 1: locked A, trying to lock B\n");

	msleep(100); // Give thread2 time to lock B

	printk(KERN_INFO "Thread 1: trying to lock B (will block)\n");
	mutex_lock(&mutex_b); // Blocked - thread2 holds B, wants A

	printk(KERN_INFO "Thread 1: locked B (should never reach)\n");
	mutex_unlock(&mutex_b);
	mutex_unlock(&mutex_a);

	return 0;
}

// Thread 2: lock B -> try lock A (reverse order - deadlock!)
static int thread2_fn(void *data)
{
	printk(KERN_INFO "Thread 2: trying to lock B\n");
	mutex_lock(&mutex_b);
	printk(KERN_INFO "Thread 2: locked B, trying to lock A\n");

	msleep(100); // Give thread1 time to lock A

	printk(KERN_INFO "Thread 2: trying to lock A (will block - DEADLOCK)\n");
	mutex_lock(&mutex_a); // Blocked - thread1 holds A, wants B

	printk(KERN_INFO "Thread 2: locked A (should never reach)\n");
	mutex_unlock(&mutex_a);
	mutex_unlock(&mutex_b);

	return 0;
}

static int __init crash_deadlock_init(void)
{
	printk(KERN_INFO "=== Mutex ABBA Deadlock Test ===\n");
	printk(KERN_INFO "Creating two threads with opposite lock order\n");

	thread1 = kthread_run(thread1_fn, NULL, "deadlock_thread1");
	thread2 = kthread_run(thread2_fn, NULL, "deadlock_thread2");

	printk(KERN_INFO "Threads started, deadlock will occur\n");
	printk(KERN_INFO "Hung task detector will find blocked threads after 120s\n");

	// CONFIG_DETECT_HUNG_TASK=y will detect and report
	// CONFIG_DEFAULT_HUNG_TASK_TIMEOUT=120

	return 0;
}

static void __exit crash_deadlock_exit(void)
{
	// Threads are deadlocked, cannot clean up properly
	if (thread1)
		kthread_stop(thread1);
	if (thread2)
		kthread_stop(thread2);

	printk(KERN_INFO "crash_deadlock: module exit\n");
}

module_init(crash_deadlock_init);
module_exit(crash_deadlock_exit);