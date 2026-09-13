import ollama

from game_rag import config


class Embedder:
    def __init__(self, client=None, model=config.EMBED_MODEL, batch_size=32):
        self.client = client if client is not None else ollama.Client()
        self.model = model
        self.batch_size = batch_size

    def embed_documents(self, texts):
        vectors = []
        # send a bunch at once, way faster than one by one
        for i in range(0, len(texts), self.batch_size):
            response = self.client.embed(model=self.model, input=texts[i:i + self.batch_size])
            vectors += [list(v) for v in response.embeddings]
        return vectors

    def embed_query(self, question):
        response = self.client.embed(model=self.model, input=config.QUERY_INSTRUCTION + question)
        return list(response.embeddings[0])
