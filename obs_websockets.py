from obswebsocket import obsws, requests as obs_requests, events
from config import Config as cfg

ws = obsws(cfg.WEBSOCKET_HOST, cfg.WEBSOCKET_PORT, cfg.WEBSOCKET_PASSWORD, timeout=1)

class Obs_Websockets:
    def connect_ws():
        ws.connect() # Connect to OBS WebSocket to control source visibility and streaming (if using OBS for audio playback)

    def disconnect_ws():
        ws.disconnect() # Disconnect from OBS WebSocket after we're done controlling the sources

    def on_visibility_change(message):
        data = message.getDatain()
        source_name = data.get('sourceName')
        is_visible = data.get('sceneItemEnabled')

        if source_name == "ListeningIcon":
            if is_visible:
                print(">>> ListeningIcon is ON. Starting listening code...")
                # CALL YOUR LISTENING FUNCTION HERE
            else:
                print(">>> ListeningIcon is OFF. Stopping/Ignoring.")
    ws.register(on_visibility_change, events.SceneItemEnableStateChanged)
