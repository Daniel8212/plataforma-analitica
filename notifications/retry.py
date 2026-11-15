import json
from notifications.service import retry
if __name__=='__main__':print(json.dumps(retry(),indent=2))
