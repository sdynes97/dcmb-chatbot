import azure.functions as func

from handlers import chat_handler, admin_handler, location_handler

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="chat", methods=["POST"])
def chat(req: func.HttpRequest) -> func.HttpResponse:
    return chat_handler.handle(req)


@app.route(route="schedule/events", methods=["GET", "POST", "DELETE"])
def admin_events(req: func.HttpRequest) -> func.HttpResponse:
    return admin_handler.handle_events(req)


@app.route(route="location", methods=["GET", "POST", "DELETE"])
def location(req: func.HttpRequest) -> func.HttpResponse:
    return location_handler.handle(req)


@app.route(route="location/track", methods=["POST"])
def location_track(req: func.HttpRequest) -> func.HttpResponse:
    return location_handler.handle_track(req)
