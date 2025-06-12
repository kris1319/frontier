import asyncio
import json
import logging

from aiohttp import web
from urllib.parse import parse_qs

from event_loop import BoundEventLoop
from simulations import failing_sim
from simulations import power_sim

bound_loop = BoundEventLoop()
routes = web.RouteTableDef()

def not_found_msg(task_id):
    """Generate a not found message for a task."""

    return f"Task with ID={task_id} doesn't exist, was cancelled before execution started or cleaned up because max tasks was reached."

def start_task(coro, name):
    """Start a task in the bound event loop."""

    task_id, task = bound_loop.add_task(coro)
    if task is None:
        msg = f"Task `{name}` with ID {task_id} has been queued and will be executed later."
    else:
        msg = f"Task `{name}` with ID {task_id} started successfully."
    return web.json_response({"status": msg, "task_id": task_id})

@routes.post('/start/power_sim')
async def start_power_sim(request):
    qs = parse_qs(request.rel_url.query_string)
    a = int(qs.get("a", ["0"])[0])
    b = int(qs.get("b", ["0"])[0])

    return start_task(power_sim(a, b), "power_sim")

@routes.post('/start/failing_sim')
async def start_failing_sim(request):
    qs = parse_qs(request.rel_url.query_string)
    a = int(qs.get("a", ["0"])[0])
    
    return start_task(failing_sim(a), "failing_sim")

@routes.post('/cancel')
async def cancel(request):
    qs = parse_qs(request.rel_url.query_string)
    task_id = int(qs.get("id", ["0"])[0])
    try:
        cancelled = bound_loop.cancel_task(task_id)
        if cancelled:
            msg = f"Task {task_id} has been cancelled"
        else:
            msg = f"Task {task_id} completed before being cancelled"
        return web.json_response({"status": msg})
    except ValueError:
        return web.json_response({"error": not_found_msg(task_id)}, status=404)
    except Exception as ex:
        return web.json_response({"error": f"An error occurred: {str(ex)}"}, status=500)

@routes.get('/status')
async def status(request):
    qs = parse_qs(request.rel_url.query_string)
    task_id = int(qs.get("id", ["0"])[0])
    try:
        status = bound_loop.get_task_status(task_id)
        if status != BoundEventLoop.TaskStatus.NOT_FOUND:
            msg = f"Task {task_id} is {status.name}"
            return web.json_response({"status": msg})
        else:
            return web.json_response({"error": not_found_msg(task_id)}, status=404)
    except Exception as ex:
        return web.json_response({"error": f"An error occurred: {str(ex)}"}, status=500)

@routes.get('/result')
async def result(request):
    qs = parse_qs(request.rel_url.query_string)
    task_id = int(qs.get("id", ["0"])[0])
    try:
        task = bound_loop.get_task(task_id)
        if task is not None:
            if task.done():
                if task.cancelled():
                    msg = f"Task {task_id} was cancelled."
                    return web.json_response({"result": msg})
                
                if task.exception() is not None:
                    msg = f"Task {task_id} failed with exception: {task.exception()}"
                    return web.json_response({"result": msg})
                
                return web.json_response({"result": task.result()})
            
            msg = f"Task {task_id} is still running."
            return web.json_response({"result": msg})
            
        else:
            msg = f"Task {task_id} hasn't been executed yet."
            return web.json_response({"result": msg})
    except ValueError:
        return web.json_response({"error": not_found_msg(task_id)}, status=404)
    except Exception as ex:
        return web.json_response({"error": f"An error occurred: {str(ex)}"}, status=500)

app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    web.run_app(app, port=8080, loop=bound_loop)