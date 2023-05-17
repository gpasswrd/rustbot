class EventTracker:
    def __init__(self):
        self.heli = 0
        self.cargo = 0
        self.eventDict = {0:self.heli, 1: self.cargo}

    def updateEvent(event_type, time):
        self.eventDict[event_type] = time