from celery import shared_task


@shared_task(name="integrations.echo")
def echo_task(message: str) -> str:
    return message
