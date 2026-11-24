import json
import threading
import time
import pika


class TelemetrySender:
    """Фоновый поток отправки телеметрии в очередь RabbitMQ."""
    def __init__(self, collector, config: dict):
        self.collector = collector
        self.config = config
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop_event.set()

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

        while not self._stop_event.is_set():
            connection = None
            try:
                connection = pika.BlockingConnection(params)
                channel = connection.channel()
                channel.queue_declare(queue=self.config["queue_name"], durable=True)
                print(f"[RabbitMQ] Подключено к {self.config['rabbitmq_host']}:{self.config['rabbitmq_port']}")

                while not self._stop_event.is_set():
                    payload = self.collector.collect()
                    payload["machine_id"] = self.config["machine_id"]

                    channel.basic_publish(
                        exchange="",
                        routing_key=self.config["queue_name"],
                        body=json.dumps(payload, ensure_ascii=False),
                        properties=pika.BasicProperties(delivery_mode=2),  # сохранять на диск
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