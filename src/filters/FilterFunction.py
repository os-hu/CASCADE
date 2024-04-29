from abc import ABC, abstractmethod



 # beim init get loaded filterfuncs

 # TODO filter all filters func      für alle entries i ndata   also für jeden einzelenne context check if all filters say true  otherweise remove form data


class FilterFunction(ABC):
    def __call__(self, *args, **kwargs):
        return self.filter(*args)

    @abstractmethod
    def filter(self, context) -> bool:
        pass
