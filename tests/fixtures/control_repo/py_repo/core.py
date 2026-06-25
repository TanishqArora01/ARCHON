class BaseController:
    pass

class ConcreteController(BaseController):
    def handle_request(self, payload: dict) -> bool:
        def validate(p: dict) -> bool:
            return "id" in p
        
        if validate(payload):
            return True
        return False


class Helper:
    def normalize(self) -> bool:
        return True


def use_helper() -> bool:
    helper = Helper()
    return helper.normalize()
