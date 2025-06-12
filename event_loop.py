import asyncio
import logging

from collections import deque
from collections import OrderedDict
from enum import Enum

class EventLoopError(Exception):
    """Exception for errors in the BoundEventLoop."""
    pass

class EventLoopQueueFullError(Exception):
    """Exception raised when BoundEventLoop task queue is full."""
    pass

class BoundEventLoop(asyncio.SelectorEventLoop):
    MAX_TASK_STATES = 1000
    MAX_TASK_QUEUE = 10
    
    class TaskStatus(Enum):
        RUNNING = 0
        QUEUED = 1
        COMPLETED = 2
        CANCELLED = 3
        FAILED = 4
        NOT_FOUND = 5

    def __init__(self, concurrency = 3):
        super().__init__()

        self._running_task_ids = set()
        self._max_concurrency = concurrency
        self._task_queue = deque()

        self._task_counter = 0
        self._tasks = OrderedDict()

    def _finalise_task(self, task_id):
        logging.debug(f"Task {task_id} has finished execution.")
        self._running_task_ids.remove(task_id)
        self._run_next_task()

    def _run_task(self, task_id, coro):
        """Create a task and start its execution."""

        logging.debug(f"Creating task {task_id} and starting execution.")
        task = self.create_task(coro)
        self._running_task_ids.add(task_id)

        if len(self._tasks) >= BoundEventLoop.MAX_TASK_STATES:
            self._tasks.popitem(last=False)
        self._tasks[task_id] = task

        task.add_done_callback(lambda t: self._finalise_task(task_id))
        return task
    
    def _get_new_task_id(self):
        """Generate a new task ID."""

        self._task_counter += 1
        return self._task_counter

    def _run_next_task(self):
        """Run the next task in the queue."""

        logging.debug(f"Run next task in the queue.")
        if self._task_queue and len(self._running_task_ids) < self._max_concurrency:
            task_id, coro = self._task_queue.popleft()
            if task_id in self._tasks:
                # the task is scheduled to run
                self._run_task(task_id, coro)
            else:
                # the task has been cancelled, let's move onto the next one
                self._run_next_task()
        else:
            # No tasks to run
            logging.debug(f"The task queue is empty, nothing to run.")
            pass

    def _queue_task(self, task_id, coro):
        """Queue a task to be run later."""

        logging.debug(f"Queueing task {task_id}.")
        self._task_queue.append((task_id, coro))
        self._tasks[task_id] = None

    def add_task(self, coro):
        """Start the coroutine and return task ID and task object.
        If the maximum concurrency is reached, the task will be queued and (ID, None) returned.
        If the task queue is full, an EventLoopQueueFullError will be raised.
        """

        logging.debug(f"Adding task to the event loop.")
        if len(self._running_task_ids) >= self._max_concurrency:
            # add the coroutine to the queue if max concurrency is reached
            if len(self._task_queue) >= BoundEventLoop.MAX_TASK_QUEUE:
                logging.error(f"Couldn't add a new task, the task queue is full (max queue size {BoundEventLoop.MAX_TASK_QUEUE}).")
                raise EventLoopQueueFullError("Task queue is full, cannot add more tasks.")

            task_id = self._get_new_task_id()
            self._queue_task(task_id, coro)
            task = None
        else:
            # start executing the coroutine immediately
            task_id = self._get_new_task_id()
            task = self._run_task(task_id, coro)

        return (task_id, task)
    
    def cancel_task(self, task_id):
        """Cancel a task by its id. If the task is running, it will be cancelled and the task
        and its status cached. If the task is queued but not yet running, it will be removed
        from the queue, the status will NOT be cached.
        """

        logging.debug(f"Cancelling task {task_id}.")
        if task_id in self._tasks:
            if self._tasks[task_id] is not None:
                return self._tasks[task_id].cancel()
            else:
                # the task is queued but not yet running, let's remove it from the queue
                # by removing the placeholder for it from the tasks dict
                logging.warning(f"Cancelling task {task_id} that is still queued. Its status will be forgotten.")
                self._tasks.pop(task_id)
                return True
            
        logging.error(f"Tried to cancel {task_id} that doesn't exist.")
        raise ValueError(f"Task with id {task_id} does not exist.")

    def get_task_status(self, task_id):
        """Get the status of a task."""

        logging.debug(f"Checking status for task {task_id}.")
        if task_id in self._running_task_ids:
            return BoundEventLoop.TaskStatus.RUNNING
        elif task_id in self._tasks:
            if self._tasks[task_id] is None:
                return BoundEventLoop.TaskStatus.QUEUED
            elif self._tasks[task_id].done():
                if self._tasks[task_id].cancelled():
                    return BoundEventLoop.TaskStatus.CANCELLED
                if self._tasks[task_id].exception() is not None:
                    return BoundEventLoop.TaskStatus.FAILED
                return BoundEventLoop.TaskStatus.COMPLETED
            else:
                # the task was scheduled, hasn't finished yet but not in the `_running_tasks`
                # this should never happen
                logging.error(f"Task {task_id} is still executing but is not in active running tasks.")
                raise EventLoopError(f"Task {task_id} is still executing but is not in active running tasks.")
        
        # the task either too old and was removed or never existed
        return BoundEventLoop.TaskStatus.NOT_FOUND

    def get_task(self, task_id):
        """Get the task object associated with the given id. Returns None if the task 
        is still being queued. Raises an exception if the task does not exist, was cancelled
        while queued or cleaned up.
        """

        if task_id in self._tasks:
            return self._tasks[task_id]
    
        logging.error(f"Tried to get {task_id} that doesn't exist.")
        raise ValueError(f"Task with id {task_id} does not exist.")
                