import arrow

async def format_seconds(seconds):
    duration = arrow.now().shift(seconds=seconds)
    if seconds < 3600:  # Check if duration is less than 1 hour
        formatted_duration = duration.format("m [minute]s and s [second]s")
    else:
        formatted_duration = duration.format("H [hour]s and m [minute]s")
    return formatted_duration

async def hours_to_seconds(currenttime:str):
    hours, minutes = currenttime.split(':')
    return (int(hours) * 3600 + int(minutes) * 60)