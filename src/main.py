import game

from fastapi import FastAPI, WebSocket
from loguru import logger

from timeit import default_timer

tx_engine = FastAPI()  # FastAPI service object that hosts TXEngine


# Implement service logic
@tx_engine.get("/")
def root_get():
    start = default_timer()
    r = game.state_device_controller.get_current_frame()
    duration = default_timer() - start
    logger.info(f"Completed state retrieval in {duration}s")
    return r


@tx_engine.put("/")
def root_put(user_input: int | str):
    start = default_timer()
    r = game.state_device_controller.deliver_input(user_input)
    duration = default_timer() - start
    logger.info(f"Completed input submission in {duration}s")
    return r


@tx_engine.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    """
    An interactive websocket endpoint. Used to communicate in real time with clients instead of in blocking-series.
    Functionally equivalent to get/put.

    Args:
        websocket: The active websocket object used to manage the connection

    Returns: None
    """

    await websocket.accept()
    while True:
        data = await websocket.receive_json()
        start = default_timer()
        r = game.state_device_controller.deliver_input(data)
        duration = default_timer() - start
        logger.info(f"Completed input submission in {duration}s")

        start = default_timer()
        r = game.state_device_controller.get_current_frame()
        duration = default_timer() - start
        logger.info(f"Completed state retrieval in {duration}s")

        await websocket.send_text(r.model_dump_json())


@tx_engine.get("/cache")
def cache(cache_path: str):
    from game.cache import get_cache

    obj: any = get_cache()
    count: int = 0

    if cache_path == r".":
        return str(obj)

    try:
        for key in cache_path.split("."):
            obj = obj[key]
            count += 1

        return str(obj)
    except KeyError:
        logger.warning("Failed to retrieve")
        return f"No value located at {cache_path}! Traveled to {'.'.join(cache_path.split('.')[:count])}"


@tx_engine.get("/cli")
def cli(command: str):
    parts = command.split(" ")

    if len(parts) < 1:
        return ""

    from game.cache import from_cache

    if parts[0] in from_cache("managers"):
        return from_cache("managers")[parts[0]].handle_command(" ".join(parts[1:]))


# Begin service logic
if __name__ == "__main__":
    exec("fastapi run")
