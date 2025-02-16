import asyncio
import websockets
import mss
import numpy as np
import cv2
import base64
from concurrent.futures import ThreadPoolExecutor

# Global flag to control the screen sharing
running = True

async def check_for_command():
    """
    This function runs in parallel with screen sharing and checks for the command
    to stop sharing. It uses a thread executor to avoid blocking the main async loop
    while waiting for user input.
    """
    global running
    # Create a thread executor for handling input
    with ThreadPoolExecutor() as executor:
        while running:
            # Wait for user input in a non-blocking way
            command = await asyncio.get_event_loop().run_in_executor(
                executor,
                input,
                "Type 'close screen share' to stop sharing: "
            )
            
            # Check if the command matches our stop phrase
            if command.lower().strip() == 'close screen share':
                print("Stopping screen share...")
                running = False
                break
            
            await asyncio.sleep(0.1)

async def send_screen(websocket, path):
    """
    Main screen sharing function that now includes command-based shutdown
    """
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            print("Screen sharing started. Type 'close screen share' to stop.")
            
            while running:
                # Capture and send screen while running is True
                screenshot = sct.grab(monitor)
                img = np.array(screenshot)
                _, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame = base64.b64encode(buffer).decode("utf-8")
                
                try:
                    await websocket.send(frame)
                except websockets.exceptions.ConnectionClosed:
                    print("Client disconnected")
                    break
                
                await asyncio.sleep(0.05)
                
    except Exception as e:
        print(f"Error in screen sharing: {e}")
    finally:
        # Clean up when the loop ends
        if not websocket.closed:
            await websocket.close()
        print("Screen sharing stopped.")

async def shutdown_server(server):
    """
    Properly shuts down the websocket server
    """
    server.close()
    await server.wait_closed()

async def main():
    """
    Main function that runs both the server and command handler simultaneously
    """
    # Start the WebSocket server
    server = await websockets.serve(send_screen, "0.0.0.0", 8765)
    
    try:
        # Run both the screen sharing server and command checker at the same time
        await asyncio.gather(
            # This keeps the server running
            asyncio.create_task(keep_server_running(server)),
            # This checks for the close command
            asyncio.create_task(check_for_command())
        )
    finally:
        # Clean shutdown when running becomes False
        await shutdown_server(server)

async def keep_server_running(server):
    """
    Keeps the server running until the running flag becomes False
    """
    global running
    while running:
        await asyncio.sleep(1)

if __name__ == "__main__":
    # Start the main event loop
    asyncio.get_event_loop().run_until_complete(main())