# VoiceBridge Local AI OS Makefile

.PHONY: start stop restart test status clean

start:
	@chmod +x start.sh stop.sh restart.sh
	@./start.sh

stop:
	@chmod +x stop.sh
	@./stop.sh

restart:
	@chmod +x start.sh stop.sh restart.sh
	@./restart.sh

download-models:
	python3 scripts/download_models.py

test:
	python3 -m pytest -v tests/

status:
	@if [ -f .server.pid ] && kill -0 $$(cat .server.pid) 2>/dev/null; then \
		PORT=$$(cat .server.port 2>/dev/null || echo 8000); \
		echo "🟢 VoiceBridge is RUNNING (PID: $$(cat .server.pid), Port: $$PORT)"; \
	else \
		echo "🔴 VoiceBridge is STOPPED"; \
	fi

clean:
	@rm -f .server.pid .local_server.log
	@find . -type d -name "__pycache__" -exec rm -rf {} +
