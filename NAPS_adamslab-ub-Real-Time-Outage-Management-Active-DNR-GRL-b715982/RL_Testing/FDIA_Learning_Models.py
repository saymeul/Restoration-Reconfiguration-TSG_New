"""
Self-contained learning models for FDIA detection.

The project environment used for testing does not always include scikit-learn,
so these models rely only on NumPy and PyTorch.
"""

import numpy as np
import torch


def fit_standardizer(X):
    mean = X.mean(axis=0).astype(np.float32)
    std = X.std(axis=0).astype(np.float32)
    std[std < 1e-6] = 1.0
    return {"mean": mean, "std": std}


def apply_standardizer(X, standardizer):
    return ((X - standardizer["mean"]) / standardizer["std"]).astype(np.float32)


def train_centroid(X, y):
    standardizer = fit_standardizer(X)
    Xs = apply_standardizer(X, standardizer)
    classes = np.unique(y)
    centroids = []
    for cls in classes:
        centroids.append(Xs[y == cls].mean(axis=0))
    return {
        "model_type": "centroid",
        "standardizer": standardizer,
        "classes": classes,
        "centroids": np.vstack(centroids).astype(np.float32),
    }


def predict_centroid(bundle, X):
    Xs = apply_standardizer(X, bundle["standardizer"])
    centroids = bundle["centroids"]
    distances = ((Xs[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
    nearest = np.argmin(distances, axis=1)
    return bundle["classes"][nearest]


def train_knn(X, y, k=5):
    standardizer = fit_standardizer(X)
    Xs = apply_standardizer(X, standardizer)
    return {
        "model_type": "knn",
        "standardizer": standardizer,
        "X_train": Xs.astype(np.float32),
        "y_train": y.astype(np.int64),
        "k": int(k),
    }


def predict_knn(bundle, X, batch_size=64):
    Xs = apply_standardizer(X, bundle["standardizer"])
    X_train = bundle["X_train"]
    y_train = bundle["y_train"]
    k = min(bundle["k"], len(y_train))
    predictions = []

    for start in range(0, len(Xs), batch_size):
        batch = Xs[start : start + batch_size]
        distances = ((batch[:, None, :] - X_train[None, :, :]) ** 2).sum(axis=2)
        nearest = np.argpartition(distances, kth=k - 1, axis=1)[:, :k]
        for row in nearest:
            votes = np.bincount(y_train[row])
            predictions.append(int(np.argmax(votes)))
    return np.array(predictions, dtype=np.int64)


class TorchDetector(torch.nn.Module):
    def __init__(self, input_dim, output_dim, model_type):
        super().__init__()
        if model_type == "linear_torch":
            self.network = torch.nn.Linear(input_dim, output_dim)
        elif model_type == "mlp_torch":
            self.network = torch.nn.Sequential(
                torch.nn.Linear(input_dim, 128),
                torch.nn.ReLU(),
                torch.nn.Dropout(0.10),
                torch.nn.Linear(128, 64),
                torch.nn.ReLU(),
                torch.nn.Linear(64, output_dim),
            )
        else:
            raise ValueError(f"Unsupported torch detector '{model_type}'")

    def forward(self, x):
        return self.network(x)


def train_torch_model(X, y, model_type, random_state=1234, epochs=80, batch_size=64, learning_rate=1e-3):
    torch.manual_seed(random_state)
    np.random.seed(random_state)

    standardizer = fit_standardizer(X)
    Xs = apply_standardizer(X, standardizer)
    input_dim = Xs.shape[1]
    output_dim = int(np.max(y)) + 1

    model = TorchDetector(input_dim, output_dim, model_type)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    loss_fn = torch.nn.CrossEntropyLoss()

    X_tensor = torch.as_tensor(Xs, dtype=torch.float32)
    y_tensor = torch.as_tensor(y, dtype=torch.long)

    for _epoch in range(epochs):
        indices = torch.randperm(len(X_tensor))
        for start in range(0, len(indices), batch_size):
            batch_idx = indices[start : start + batch_size]
            logits = model(X_tensor[batch_idx])
            loss = loss_fn(logits, y_tensor[batch_idx])
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

    return {
        "model_type": model_type,
        "standardizer": standardizer,
        "input_dim": input_dim,
        "output_dim": output_dim,
        "state_dict": model.state_dict(),
    }


def predict_torch_model(bundle, X, batch_size=256):
    Xs = apply_standardizer(X, bundle["standardizer"])
    model = TorchDetector(bundle["input_dim"], bundle["output_dim"], bundle["model_type"])
    model.load_state_dict(bundle["state_dict"])
    model.eval()

    predictions = []
    with torch.no_grad():
        for start in range(0, len(Xs), batch_size):
            batch = torch.as_tensor(Xs[start : start + batch_size], dtype=torch.float32)
            logits = model(batch)
            predictions.append(torch.argmax(logits, dim=1).cpu().numpy())
    return np.concatenate(predictions).astype(np.int64)


def train_detector_model(model_name, X, y, random_state=1234, epochs=80):
    if model_name == "centroid":
        return train_centroid(X, y)
    if model_name == "knn":
        return train_knn(X, y, k=5)
    if model_name in {"linear_torch", "mlp_torch"}:
        return train_torch_model(X, y, model_name, random_state=random_state, epochs=epochs)
    raise ValueError(f"Unknown model '{model_name}'")


def predict_detector_model(bundle, X):
    model_type = bundle["model_type"]
    if model_type == "centroid":
        return predict_centroid(bundle, X)
    if model_type == "knn":
        return predict_knn(bundle, X)
    if model_type in {"linear_torch", "mlp_torch"}:
        return predict_torch_model(bundle, X)
    raise ValueError(f"Unknown model type '{model_type}'")
