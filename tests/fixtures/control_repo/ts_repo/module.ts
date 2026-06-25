export interface Payload {
    id: string;
}

export class BaseService {
    protected name: string = "Base";
}

export interface IService {}

export class ConcreteService extends BaseService implements IService {
    public process(payload: Payload): boolean {
        const validate = (p: Payload): boolean => {
            return p.id !== "";
        };

        return validate(payload);
    }
}
