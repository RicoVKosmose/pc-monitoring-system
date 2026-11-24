import json
import threading
import pika


class TelemetrySender:
    """Фоновый поток отправки телеметрии в Topic Exchange RabbitMQ."""
    def __init__(self, collector, config: dict):
        self.collector = collector
        self.config = config
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _detect_alerts(self, payload: dict) -> list[str]:
        """Проверяет превышение пороговых значений для маршрутизации в очередь алертов."""
        limits = self.config["thresholds"]
        alerts = []

        cpu = payload["cpu"]["usage_percent"]
        if cpu >= limits["cpu_percent"]:
            alerts.append(f"Высокая загрузка CPU: {cpu:.1f}%")

        gpu = payload["gpu"]
        if gpu["available"] and gpu["usage_percent"] is not None:
            if gpu["usage_percent"] >= limits["gpu_percent"]:
                alerts.append(f"Высокая загрузка GPU: {gpu['usage_percent']:.1f}%")

        ram = payload["memory"]["percent"]
        if ram >= limits["memory_percent"]:
            alerts.append(f"Высокое потребление RAM: {ram:.1f}%")

        disk = payload["disk"]["percent"]
        if disk >= limits["disk_percent"]:
            alerts.append(f"Мало места на диске {payload['disk']['device']}: {disk:.1f}%")

        return alerts

    def _run(self):
        credentials = pika.PlainCredentials(
            self.config["rabbitmq_user"],
            self.config["rabbitmq_pass"],
        )
        params = pika.ConnectionParameters(
            host=self.config["rabbitmq_host"],
            port=self.config["rabbitmq_port"],
            credentials=credentials,
            heartbeat=30,
        )
        exchange = self.config["exchange_name"]

        while not self._stop_event.is_set():
            connection = None
            try:
                connection = pika.BlockingConnection(params)
                channel = connection.channel()
                channel.exchange_declare(
                    exchange=exchange,
                    exchange_type="topic",
                    durable=True,
                )
                print(
                    f"[RabbitMQ] Подключено к {self.config['rabbitmq_host']}:{self.config['rabbitmq_port']} "
                    f"(exchange: '{exchange}')"
                )

                while not self._stop_event.is_set():
                    payload = self.collector.collect()
                    payload["machine_id"] = self.config["machine_id"]

                    alerts = self._detect_alerts(payload)
                    payload["alerts"] = alerts
                    routing_key = "telemetry.alert" if alerts else "telemetry.normal"

                    channel.basic_publish(
                        exchange=exchange,
                        routing_key=routing_key,
                        body=json.dumps(payload, ensure_ascii=False),
                        properties=pika.BasicProperties(delivery_mode=2),
                    )
                    self._stop_event.wait(self.config["send_interval_sec"])

            except Exception as e:
                print(f"[RabbitMQ] Нет связи ({e}). Повтор через 5 сек...")
                self._stop_event.wait(5)
            finally:
                if connection and not connection.is_closed:
                    try:
                        connection.close()
                    except Exception:
                        pass