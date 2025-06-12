## Endpoints

I implemented API for the task manager based on HTTP server with endpounts:
  * POST start/{task}
  * POST cancel?id={task_id}
  * GET status?id={task_id}
  * GET result?id={task_id}

I didn't have much time to implement pause/resume mechanism but have ideas on
how I would do it. 

## Implementation details

The task manager supports 3 concrurrently running tasks and queues all new
tasks unless the queue limit is reached. When a running task completed, next
task from the queue starts automatically executing. 
Result of the completed task is cached within the event loop for easy access
to the task result/status. The reason the task object is cached and not just
left for the client to hold is because the client doesn't know when the 
execution is actually going to start, i.e. when the task object is created.
When the size limit on the cache is reached, the oldest task gets cleaned up.

There is a one caveat with task cancellation.
I allow to cancel a task that has been queued but not yet executed. Because
that means that the task object hasn't been created yet, there is no status
to cache. Meaning the task manager will "forget" that the task with such ID
existed and was cancelled.
There are couple of workarounds:
  * Don't allow to cancel queued tasks
  * Keep separate container for such tasks
  * Rething the "caching" alltogether
I left as is for simplicity. 

Max queue size is 10.
Max "cache" size is 1000.

All these parameters and more can be configurable through cli args but for 
simplisity those are constant.

## Simulations

There are two long running operations defined:
  * `power_sim(a, b, delay_seconds = 5)` which sleeps on each multiplication
    for `delay_seconds` time and returns the result
  * `failing_sim(a, delay_seconds = 5)` which sleeps on each multiplication
    for `delay_seconds` time and raises an exception in the end

## How to run 

To run the task manager:
```
$ python3 frontier/async_http_server.py
```

To start tasks:
```
$ curl -X POST "http://localhost:8080/start/power_sim?a=2&b=20"

$ curl -X POST "http://localhost:8080/start/failing?a=2"
```

To cancel a task:
```
$ curl -X POST "http://localhost:8080/cancel?id=4"
```

To get status and result:
```
$ curl "http://localhost:8080/status?id=1"

$ curl "http://localhost:8080/result?id=7"
```
