# RTSP Stream Viewer

This project allows users to view RTSP streams in their web browser.

## Project Overview

The application is built with a React frontend and a Django backend.

### Screenshot
![Stream View](./assets/rtsp_ss1.png)
![Stream View](./assets/rtsp_ss2.png)


**Frontend:**
*   **Framework/Libraries:** React, Tailwind CSS, Shadcn/ui
*   **Build Tool:** Vite

**Backend:**
*   **Framework:** Django, Django REST Framework (for APIs)
*   **WebSockets:** Django Channels with Daphne
*   **RTSP Processing:** FFmpeg is used to connect to RTSP streams, convert them to MJPEG, and we send it to frontend in chunks of 2MB. And at frontend we queue this in a frame queue for smoothly showing the video.

## Key Features & Approach
*   **Create Multiple Streams:** Users can create multiple streams using RTSP URLs.
*   **WebSocket Stream Handling:** When a user connects to view a stream via WebSocket, the connection's `stream_id` is mapped to an RTSP instance. If another user joins the same `stream_id`, the existing RTSP instance and its processed stream can be broadcast to multiple users. In RTSP instance we use FFmpeg to listen on the RTSP stream.
*   **MJPEG over Websocket:** Video frames are taken from the RTSP source using FFmpeg, converted to MJPEG format, and then sent to the frontend as bytes through WebSockets. We are making 2 MB chunks here.
*   **Buffer queue in frontend:** In frontend we are using a buffer queue to store some frames (and not showing immediately). This helps us show smooth stream and get over the inconsistent network delays and failures.
*   **Note on Performance:** Currently, streams are processed at 10 FPS. This is a deliberate choice to ensure smooth operation on low-compute environments. This can be adjusted in `stream/utils/rtsp_client.py` by changing the `self.fps` attribute and the `fps={self.fps}` value in the FFmpeg command.
*   **Stream Cleanup:** Instead of cleaning up FFmpeg processes immediately when a client disconnects, a periodic task (`cleanup_streams` in `stream/consumer.py`) checks for inactive streams (client_count == 0) and shuts them down. This approach can be more robust in handling abrupt disconnections.


## How to Run the Project

### Prerequisites
*   Docker
*   An RTSP stream source (you can use the provided `demo_rtsp_server` or your own)

### Using Docker Compose (Recommended)

1.  **Run the Docker image:**
    ```bash
    docker compose up -d
    ```

    The application will be accessible at `http://localhost:8000`.
    The admin panel is at `http://localhost:8000/admin` with credentials `admin@gmail.com` / `Admin@123`.

### Running the Demo RTSP Server (Optional)



If you want to use the provided demo RTSP server:

1.  Navigate to the `demo_rtsp_server` directory:
    ```bash
    cd demo_rtsp_server
    ```
2.  Start the RTSP server using Docker Compose:
    ```bash
    docker compose up -d
    ```

3. Use this command to stream your local file to rtsp server via ffmpeg
    ```bash
    ffmpeg -re -stream_loop -1 -i ./samples/input_files/sample.mp4 -c copy -f rtsp rtsp://localhost:8554/local-loop
    ```

    This will start an RTSP server at `rtsp://localhost:8554/local-loop` streaming a sample video. You can use this URL in the application.

### Local Development (Without Docker)

Refer to the `Makefile` for commands to run the frontend and backend separately. You'll need Python (with `uv` for package management and a virtual environment), Node.js (with `bun` for the frontend), and `ffmpeg` installed on your system.

1.  **Install backend dependencies:**
    ```bash
    # Assuming you have uv installed and you are in venv
    uv pip install -e .
    ```
2.  **Install frontend dependencies:**
    ```bash
    cd ui
    bun install
    ```
3.  **Run the backend (Django + Daphne):**
    (You might need to adapt this based on your `Makefile` or `manage.py` setup for Daphne)
    ```bash
    # First, run migrations and create superuser if not done
    python manage.py makemigrations
    python manage.py migrate
    
    # If you want to create admin user you can run the below commented script
    # echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@gmail.com', 'Admin@123')" | python manage.py shell

    # If you want to run your local rtsp server for testing cd demo_rtsp_server && docker compose up -d && ffmpeg -re -stream_loop -1 -i <your_file_path_to_video> -c copy -f rtsp rtsp://localhost:8554/local-loop

    # Then run django server using their cli
    python manage.py runserver
    ```
4.  **Run the frontend (Vite dev server):**
    ```bash
    cd ui
    bun run dev
    ```
    The frontend will be available at `http://localhost:3000` or a similar port, and will connect to the backend at port 8000.



## Project Structure

*(Placeholder: Briefly describe the main directories and their purpose, e.g., `ui/` for frontend, `rtsppy/` for main Django app, `stream/` for stream handling logic)*

```
.
├── Dockerfile
├── Makefile
├── README.md
├── assets/             
├── demo_rtsp_server/   # Contains a sample local RTSP server setup
├── manage.py           # Django's command-line utility
├── pyproject.toml      # Python project metadata and dependencies
├── rtsppy/             # Main Django project directory
├── stream/             # Django app for stream handling RTSP and stream related APIs
├── ui/                 # Frontend React application

```

## Future Scope / Production Readiness

*   **Scalability & State Management:**
    *   Externalize `active_streams` (e.g., Redis) for horizontal scaling.
    *   Implement distributed task queues (e.g., Celery, Django Q).
*   **Performance Optimization:**
    *   Use more optimal frame queue in frontend and handle FPS automatically.
    *   Adjust FPS with respect to load on server.
    *   Tune FFmpeg: dynamic parameters, explore alternatives (WebRTC, HLS, DASH).
*   **User Experience & Features:**
    *   Improve multi-stream display (tiling/grid layout).
    *   Allow user-managed streams (add, configure via UI).
    *   Implement stream discovery/previews.
*   **Robustness & Reliability:**
    *   Use python-bindings for ffmpeg insted of self maanging process. and Advanced FFmpeg error handling (monitoring, restarting).
    *   Graceful degradation for connection/source issues.
    *   Refine connection management for distributed environments.
