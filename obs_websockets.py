from obswebsocket import obsws, requests as obs_requests
from config import Config as cfg

ws = obsws(cfg.WEBSOCKET_HOST, cfg.WEBSOCKET_PORT, cfg.WEBSOCKET_PASSWORD, timeout=1)

class Obs_Websockets:
    def connect_ws():
        ws.connect() # Connect to OBS WebSocket to control source visibility and streaming (if using OBS for audio playback)

    def disconnect_ws():
        ws.disconnect() # Disconnect from OBS WebSocket after we're done controlling the sources
