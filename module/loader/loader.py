from torch.utils.data import DataLoader
from torchvision import transforms
from torchvision import datasets
from ..utils import Progress
import torch
import difflib


def load_dataset(
    name: str, root: str, batch_size: int, num_workers: int
) -> tuple[DataLoader, DataLoader]:
    """
    Get the train and test loaders for a dataset.

    Args:
        name (str): The name of the dataset.
        root (str): The root directory where the dataset will be stored.
        batch_size (int): The batch size.
        num_workers (int): The number of workers for the DataLoader.

    Returns:
        tuple[DataLoader, DataLoader]: The train and test loaders.
    """
    data_module = get_dataset(name)

    # Get the mean and standard deviation of the dataset
    temp_dataset = data_module(
        root=root, download=True, transform=transforms.ToTensor()
    )
    temp_loader = DataLoader(
        temp_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers
    )
    mean, std_dev, size = get_dataset_info(temp_loader)

    # get transformation functions
    train_transform = transforms.Compose(
        [
            transforms.RandomCrop(size, padding=4),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize(mean, std_dev),
        ]
    )
    test_transform = transforms.Compose(
        [
            transforms.ToTensor(),
            transforms.Normalize(mean, std_dev),
        ]
    )

    # Get datasets
    train_dataset = data_module(
        root=root, train=True, download=True, transform=train_transform
    )
    test_dataset = data_module(
        root=root, train=False, download=True, transform=test_transform
    )

    # Get data loaders
    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True, num_workers=num_workers
    )
    test_loader = DataLoader(
        test_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers
    )

    return train_loader, test_loader


def get_dataset(name: str) -> datasets.VisionDataset:
    """
    Get a dataset from torchvision.datasets.

    Args:
        name (str): The name of the dataset.

    Returns:
        datasets.VisionDataset: The dataset.
    """
    # Remove spaces and convert to lowercase
    name = name.lower().strip().replace(" ", "")
    dataset_names = {
        name.lower(): name for name in dir(datasets) if not name.startswith("_")
    }

    # If dataset exists return it
    if name in dataset_names:
        return getattr(datasets, dataset_names[name])

    # Otherwise, raise an error with suggestions
    matches = difflib.get_close_matches(name, dataset_names.keys(), cutoff=0)
    raise ValueError(
        f"Dataset {name} not found. Did you mean [{', '.join([dataset_names[m] for m in matches])}]?"
    )


def get_dataset_info(
    data_loader: DataLoader,
) -> tuple[tuple[float], tuple[float], tuple[int, int]]:
    """
    Compute the mean, standard deviation, and size of the dataset.

    Args:
        data_loader (DataLoader): A PyTorch DataLoader containing the dataset.

    Returns:
        means, standard deviations, and size of the dataset.
    """
    mean_sum = torch.zeros(3)
    std_sum = torch.zeros(3)
    num_samples = 0
    image_size = None  # To store (height, width) of a single image

    for images, _ in data_loader:
        # Batch size and number of channels
        batch_size = images.size(0)
        num_samples += batch_size

        # Store image dimensions (assume all images have the same size)
        if image_size is None:
            _, _, height, width = images.size()
            image_size = (height, width)

        # Flatten the image dimensions (batch_size, channels, height * width)
        images = images.view(batch_size, images.size(1), -1)

        # Accumulate batch-level means and standard deviations
        mean_sum += images.mean(dim=(0, 2)) * batch_size
        std_sum += images.std(dim=(0, 2)) * batch_size

    # Compute overall means and standard deviations
    means = tuple((mean_sum / num_samples).tolist())
    std_devs = tuple((std_sum / num_samples).tolist())

    return means, std_devs, image_size
