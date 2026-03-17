from obswebsocket import obsws, requests as obs_requests, events
from config import Config as cfg

ws = obsws(cfg.WEBSOCKET_HOST, cfg.WEBSOCKET_PORT, cfg.WEBSOCKET_PASSWORD, timeout=1)

class Obs_Websockets:
    def connect_ws():
        ws.connect() # Connect to OBS WebSocket to control source visibility and streaming (if using OBS for audio playback)

    def disconnect_ws():
        ws.disconnect() # Disconnect from OBS WebSocket after we're done controlling the sources

    def on_visibility_change(message):
        print(message)
        source_id = message.getSceneItemId()
        is_visible = message.getSceneItemEnabled()
        #scene_name = message.getSceneName()
        #source_name = ws.call(obs_requests.GetSceneItemSource(sceneName=scene_name, sceneItemId=source_id))

        if source_id == 82: # ListeningIcon
            if is_visible:
                print(">>> ListeningIcon is ON. Starting listening code...")
                # CALL YOUR LISTENING FUNCTION HERE
            else:
                print(">>> ListeningIcon is OFF. Stopping/Ignoring.")
    ws.register(on_visibility_change, events.SceneItemEnableStateChanged)
