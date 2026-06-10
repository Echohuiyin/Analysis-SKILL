/*
 * Cache Deadlock Reproducer
 * 
 * Purpose: Reproduce ABBA mutex deadlock from vmcore analysis
 * 
 * Root cause (from vmcore):
 *   - Task1: holds mutex_cache_read, waits for mutex_cache_write
 *   - Task2: holds mutex_cache_write, waits for mutex_cache_read
 *   - Classic lock order violation
 * 
 * This reproducer intentionally creates the same deadlock pattern
 * to trigger hung task detection.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/mutex.h>
#include <linux/kthread.h>
#include <linux/delay.h>

/* Two mutexes that will deadlock */
static DEFINE_MUTEX(mutex_cache_read);
static DEFINE_MUTEX(mutex_cache_write);

/* Thread structures */
static struct task_struct *thread1;
static struct task_struct *thread2;

/*
 * Thread 1: Acquire read mutex first, then write mutex
 * 
 * Pattern from vmcore analysis:
 *   cache_flush_worker() {
 *     mutex_lock(&mutex_cache_read);  // acquired
 *     msleep(100);                    // delay to allow race
 *     mutex_lock(&mutex_cache_write); // BLOCKED - waiting for thread2
 *   }
 */
static int cache_flush_thread(void *data)
{
    printk(KERN_INFO "cache_flush_thread: starting\n");
    
    mutex_lock(&mutex_cache_read);
    printk(KERN_INFO "cache_flush_thread: acquired mutex_cache_read\n");
    
    /* Delay to create race condition window */
    msleep(100);
    
    printk(KERN_INFO "cache_flush_thread: trying to acquire mutex_cache_write\n");
    mutex_lock(&mutex_cache_write);
    
    /* This line will never execute due to deadlock */
    printk(KERN_INFO "cache_flush_thread: acquired both mutexes\n");
    mutex_unlock(&mutex_cache_write);
    mutex_unlock(&mutex_cache_read);
    
    return 0;
}

/*
 * Thread 2: Acquire write mutex first, then read mutex
 * 
 * Pattern from vmcore analysis:
 *   cache_read_worker() {
 *     mutex_lock(&mutex_cache_write); // acquired
 *     msleep(100);                    // delay to allow race
 *     mutex_lock(&mutex_cache_read);  // BLOCKED - waiting for thread1
 *   }
 */
static int cache_read_thread(void *data)
{
    printk(KERN_INFO "cache_read_thread: starting\n");
    
    mutex_lock(&mutex_cache_write);
    printk(KERN_INFO "cache_read_thread: acquired mutex_cache_write\n");
    
    /* Delay to create race condition window */
    msleep(100);
    
    printk(KERN_INFO "cache_read_thread: trying to acquire mutex_cache_read\n");
    mutex_lock(&mutex_cache_read);
    
    /* This line will never execute due to deadlock */
    printk(KERN_INFO "cache_read_thread: acquired both mutexes\n");
    mutex_unlock(&mutex_cache_read);
    mutex_unlock(&mutex_cache_write);
    
    return 0;
}

static int __init deadlock_reproducer_init(void)
{
    printk(KERN_INFO "=== Cache Deadlock Reproducer Loaded ===\n");
    printk(KERN_INFO "This module creates ABBA mutex deadlock\n");
    printk(KERN_INFO "Expected: hung task after 120 seconds\n");
    
    /* Create two threads with opposite lock order */
    thread1 = kthread_run(cache_flush_thread, NULL, "cache_flush");
    thread2 = kthread_run(cache_read_thread, NULL, "cache_read");
    
    if (!thread1 || !thread2) {
        printk(KERN_ERR "Failed to create threads\n");
        return -ENOMEM;
    }
    
    printk(KERN_INFO "Threads started, deadlock will occur shortly\n");
    
    return 0;
}

static void __exit deadlock_reproducer_exit(void)
{
    /* Module will likely hang, but cleanup code here anyway */
    printk(KERN_INFO "Cache Deadlock Reproducer unloaded\n");
}

module_init(deadlock_reproducer_init);
module_exit(deadlock_reproducer_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Kernel Testcase Generator");
MODULE_DESCRIPTION("Reproducer for cache mutex ABBA deadlock");
MODULE_VERSION("1.0");
