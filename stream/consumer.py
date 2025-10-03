# streams/consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import json
from .utils.rtsp_client import RTSPClient
from .models import Stream
from asgiref.sync import sync_to_async
import logging
import threading
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('rtsp_consumer')

# Simple global dict to track active streams
active_streams : dict[str, RTSPClient] = {}

# Background task to clean up streams that should be removed
async def cleanup_streams():
    """Periodically check and remove streams marked for removal"""
    while True:
        logger.info(f"Periodic cleanup of streams")
        await asyncio.sleep(30)  # Check every 5 seconds
        to_remove = []
        for stream_id, client in active_streams.items():
            if client.client_count == 0:
                to_remove.append(stream_id)
        
        for stream_id in to_remove:
            logger.info(f"Cleanup: Removing stream {stream_id} from active streams")
            if active_streams[stream_id]:
                logger.info(f"Shutting down stream {stream_id} with client count {active_streams[stream_id].client_count}")
                active_streams[stream_id]._shutdown()
            logger.info(f"Deleting stream {stream_id} from active streams")
            del active_streams[stream_id]

class RTSPConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handle new client connection"""
        logger.info('RTSP Consumer connect initiated')
        
        self.stream_id = self.scope['url_route']['kwargs']['stream_id']

        self.group_name = f'stream_{self.stream_id}'

        client_id = self.scope['client'][1]
        print(f"RTSP Consumer connect initiated for stream {client_id}")
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f'Client connected to stream {self.stream_id}')
        
        try:
            stream = await sync_to_async(Stream.objects.get)(id=self.stream_id, is_active=True)
            url = stream.url
        except Stream.DoesNotExist:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Stream not found'
            }))
            await self.close()
            return
        
        if self.stream_id in active_streams:
            client = active_streams[self.stream_id]
            client.add_client()
            await self.send(text_data=json.dumps({
                'type': 'status',
                'message': 'Joined existing stream'
            }))
        else:
            client = RTSPClient(self.stream_id, url, self.group_name)
            active_streams[self.stream_id] = client
            client.start()
            await self.send(text_data=json.dumps({
                    'type': 'status',
                    'message': 'Started new stream'
                }))
            
        # Make sure cleanup task is running
        for task in asyncio.all_tasks():
            if task.get_name() == 'cleanup_streams':
                break
        else:
            # Start cleanup task if not already running
            cleanup_task = asyncio.create_task(cleanup_streams())
            cleanup_task.set_name('cleanup_streams')

    async def disconnect(self, close_code):
        """Handle client disconnection"""
        logger.info(f'Client disconnecting from stream {self.stream_id}')
        
        # Leave room group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        
        # Remove client from stream
        def remove_client():
            if self.stream_id in active_streams:
                client = active_streams[self.stream_id]
            client.remove_client()
            if client.client_count == 0:
                del active_streams[self.stream_id]
                
        await sync_to_async(remove_client)()
        logger.info(f'Client disconnected from stream {self.stream_id}')
    
    async def receive(self, text_data):
        """Handle client sending messages"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'ping':
                # Simple keepalive response
                await self.send(text_data=json.dumps({
                    'type': 'pong'
                }))
            
        except json.JSONDecodeError:
            pass
    
    async def stream_frame(self, event):
        """Send a video frame to the client"""
        try:
            # await self.send(text_data=json.dumps({
            #     'type': 'stream_frame',
            #     'frame': event['frame'],
            #     'stream_id': event['stream_id']
            # }))
            await self.send(bytes_data=event['frame'])
        except Exception as e:
            logger.error(f"Error sending frame to client: {str(e)}")
    
    async def stream_status(self, event):
        """Send status message to client"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'stream_status',
                'message': event['message'],
                'stream_id': event['stream_id']
            }))
        except Exception as e:
            logger.error(f"Error sending status to client: {str(e)}")
    
    async def stream_error(self, event):
        """Send error message to client"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'stream_error',
                'message': event['message'],
                'stream_id': event['stream_id']
            }))
        except Exception as e:
            logger.error(f"Error sending error to client: {str(e)}")
        
