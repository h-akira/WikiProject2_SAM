import sys
import os
from hadx.handler import Master

def lambda_handler(event, context):
  sys.path.append(os.path.dirname(__file__))
  master = Master(event, context)
  master.logger.info(f"path: {master.request.path}")
  master.logger.info(f"event: {event}")
  # master.settings.COGNITO.set_auth_by_code(master)
  master.settings.COGNITO.set_auth_by_cookie(master)
  try:
    view, kwargs = master.router.path2view(master.request.path)
    response = view(master, **kwargs)
    master.settings.COGNITO.add_set_cookie_to_header(master, response)
    master.logger.info(f"response: {response}")
    return response
  except Exception as e:
    if master.request.path == "/favicon.ico":
      master.logger.warning("favicon.ico not found")
    else:
      master.logger.exception(e)
    from hadx.shortcuts import error_render
    import traceback
    return error_render(master, traceback.format_exc())
