import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883
TOPIC = "tima/execution-events"
CLIENT_ID = "tima-debug-execution-events"
QOS = 1


def on_connect(client, userdata, flags, rc, properties=None):
    _ = userdata, properties
    print(f"Connected with result code {rc}")
    result, mid = client.subscribe(TOPIC, qos=QOS)
    print(f"Subscribed to topic: {TOPIC} (qos={QOS}, result={result}, mid={mid})")


def on_disconnect(client, userdata, rc, properties=None):
    _ = client, userdata, properties
    print(f"Disconnected with result code {rc}")


def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    _ = client, userdata, properties
    print(f"Subscribe acknowledged: mid={mid}, granted_qos={granted_qos}")


def on_message(client, userdata, msg):
    _ = userdata
    print(
        f"Message received on {msg.topic} "
        f"(qos={msg.qos}, retain={msg.retain}, dup={msg.dup}): {msg.payload.decode()}"
    )


def main():
    client = mqtt.Client(
        client_id=CLIENT_ID,
        clean_session=False,
        protocol=mqtt.MQTTv311,
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=5)
    client.connect(BROKER, PORT, 60)
    print(
        f"Listening for messages on {TOPIC} with client_id={CLIENT_ID}, qos={QOS}. "
        "Press Ctrl+C to exit."
    )
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Exiting...")


if __name__ == "__main__":
    main()
