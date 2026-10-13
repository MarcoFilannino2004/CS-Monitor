class Categoria:

    def __init__(self, id_categoria: int, nome: str):
        self.id_categoria = id_categoria
        self.nome = nome

    @property
    def id_categoria(self):
        return self._id_categoria

    @id_categoria.setter
    def id_categoria(self, valore):
        if type(valore) is not int or valore <= 0:
            raise ValueError("L'ID della categoria deve essere un intero positivo.")
        self._id_categoria = valore

    @property
    def nome(self):
        return self._nome

    @nome.setter
    def nome(self, valore):
        if not isinstance(valore, str) or not valore.strip():
            raise ValueError("Il nome della categoria non può essere vuoto.")
        self._nome = valore.strip()

    def __str__(self):
        return f"{self.id_categoria} - {self.nome}"
