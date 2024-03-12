SLACK_CHANNEL = "meerkat-obs-log"
SLACK_PROXY_CHANNEL = "slack-messages"

def alert(r, message, name, slack_channel=SLACK_CHANNEL,
          slack_proxy_channel=SLACK_PROXY_CHANNEL):
    """Publish a message to the alerts Slack channel.
    Args:
        message (str): Message to publish to Slack.
        name (str): Name of process issuing the alert.
        slack_channel (str): Slack channel to publish message to.
        slack_proxy_channel (str): Redis channel for the Slack proxy/bridge.
    Returns:
        None
    """
    # Format: <Slack channel>:<Slack message text>
    alert_msg = f"{slack_channel}:[{timestring()} - {name}] {message}"
    r.publish(slack_proxy_channel, alert_msg)

def timestring():
    """A standard format to report the current time in"""
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")