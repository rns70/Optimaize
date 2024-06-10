import websockets.sync.client as ws

# For ease of development we will make the websocket client a singleton
class WebSocketClient:
    __instance = None

    @staticmethod
    def i():
        if WebSocketClient.__instance == None:
            WebSocketClient.__instance = WebSocketClient()
        return WebSocketClient.__instance

    def __init__(self):
        if WebSocketClient.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            WebSocketClient.__instance = self

        self.ws = ws.connect("ws://localhost:8085")

    def send(self, message):
        # Set timeout to 1 second
        self.ws.send(message)

    def receive(self):
        self.ws.recv()

    def close(self):
        self.ws.close()