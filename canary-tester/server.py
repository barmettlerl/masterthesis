from asgiref.wsgi import WsgiToAsgi
from flask import Flask, request, jsonify
import threading
from logging.config import dictConfig
import logging
import os
import datetime as dt
import canary_tester.experiment as experiment
from canary_tester.types import RunningThread


LOG_LEVEL = int(os.getenv("LOG_LEVEL", logging.INFO))

dictConfig({
    "version": 1,
    "formatters": {
        "default": {
            "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
        }
    },
    "handlers": {
        "wsgi": {
            "class": "logging.StreamHandler",
            "stream": "ext://flask.logging.wsgi_errors_stream",
            "formatter": "default",
        }
    },
    "root": {"level": LOG_LEVEL, "handlers": ["wsgi"]},
})

logger = logging.getLogger("root")

app = Flask(__name__)


thread = RunningThread()


def worker_loop(data):
    global thread
    try:
        experiment.run(
            data["version_under_test"],
            data["max_time_s"],
            data["fetch_interval_s"],
            data["start_time"],
            data["control_group_versions"],
            data["simulation_speedup_factor"],
            thread,
        )
    except Exception as e:
        logger.info(f"experiment stopped: {e}")
    finally:
        with thread.lock:
            thread.finished = True
            thread.should_stop = False
            thread.started = True


@app.route("/start", methods=["POST"])
async def start_experiment():
    global thread

    data = request.get_json(force=True)

    if data["version_under_test"] is None:
        return jsonify({"error": "version_under_test is required"}), 400
    if data["max_time_s"] is None:
        return jsonify({"error": "max_time_s is required"}), 400
    if data["fetch_interval_s"] is None:
        return jsonify({"error": "fetch_interval_s is required"}), 400
    if "start_time" not in data:
        data["start_time"] = None
    if "control_group_versions" not in data:
        data["control_group_versions"] = []
    if "simulation_speedup_factor" not in data:
        data["simulation_speedup_factor"] = 1

    if data["start_time"] is not None:
        start = dt.datetime.fromtimestamp(int(data["start_time"]))
        end = start + dt.timedelta(seconds=int(data["max_time_s"]))
        now = dt.datetime.now()
        if end > now:
            return jsonify({"error": "end of experiment is in the future"}), 400

    with thread.lock:
        if thread.started and thread.finished and thread.thread is not None:
            thread.thread.join()
            thread.finished = False
            thread.started = True
            thread.should_stop = False
            thread.thread = threading.Thread(
                target=worker_loop, daemon=True, args=(data,)
            )
            thread.thread.start()
            return jsonify({"message": "Experiment started"}), 200
        elif thread.thread is not None and thread.started and not thread.finished:
            return jsonify({"error": "Experiment already running"}), 400
        else:
            thread.started = True
            thread.should_stop = False
            thread.finished = False
            thread.thread = threading.Thread(
                target=worker_loop, daemon=True, args=(data,)
            )
            thread.thread.start()

            return jsonify({"message": "Experiment started"}), 200


@app.route("/stop", methods=["POST"])
async def stop_experiment():
    global thread

    with thread.lock:
        thread.should_stop = True

    return jsonify({"message": "Experiment stopped"}), 200


@app.route("/healthz", methods=["GET"])
def healthz():
    return "True"


asgi_app = WsgiToAsgi(app)


if __name__ == "__main__":
    asgi_app.run(debug=True)
