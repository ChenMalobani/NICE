"""Training procedure for NICE.
"""

import argparse
import torch, torchvision
import numpy as np
import nice, utils
import matplotlib.pyplot as plt
import os

# N = 100
#
#


def train(flow, trainloader, optimizer, device, dataset):
    flow.train()  # set to training mode
    running_loss = 0
    for n_batches, data in enumerate(trainloader,1):
        optimizer.zero_grad()
        inputs, _ = data
        inputs = utils.prepare_data(
            inputs, dataset).to(device)
        loss = -flow(inputs).mean()
        running_loss += float(loss)
        loss.backward()
        optimizer.step()
    return running_loss / n_batches


def test(flow, testloader, epoch, filename, device, dataset):
    flow.eval()  # set to inference mode
    running_loss = 0
    with torch.no_grad():
        samples = flow.sample(100).cpu()
        samples = utils.prepare_data(samples, dataset, reverse=True)
        torchvision.utils.save_image(torchvision.utils.make_grid(samples),
                                     './samples/' + filename + '_epoch%d.png' % epoch)
        for n_batches, data in enumerate(testloader,1):
            inputs, _ = data
            inputs = utils.prepare_data(
                inputs, dataset).to(device)
            loss = -flow(inputs).mean()
            running_loss += float(loss)
    return running_loss / n_batches


def main(args):
    device = torch.device("cuda:0")

    # model hyperparameters
    dataset = args.dataset
    batch_size = args.batch_size
    latent = args.latent
    max_iter = args.max_iter
    sample_size = args.sample_size
    coupling = args.coupling
    mask_config = 1.

    # optimization hyperparameters
    lr = args.lr
    momentum = args.momentum
    decay = args.decay

    zca = None
    mean = None
    if dataset == 'mnist':
        mean = torch.load('./statistics/mnist_mean.pt')
        (full_dim, mid_dim, hidden) = (1 * 28 * 28, args.mid_dim, args.hidden)
        transform = torchvision.transforms.ToTensor()
        trainset = torchvision.datasets.MNIST(root='~/torch/data/MNIST',
                                              train=True, download=True, transform=transform)
        trainloader = torch.utils.data.DataLoader(trainset,
                                                  batch_size=batch_size, shuffle=True, num_workers=2)
        testset = torchvision.datasets.MNIST(root='./data/MNIST',
                                             train=False, download=True, transform=transform)
        testloader = torch.utils.data.DataLoader(testset,
                                             batch_size=args.batch_size, shuffle=False, num_workers=1)

    elif dataset == 'fashion-mnist':
        mean = torch.load('./statistics/fashion_mnist_mean.pt')
        (full_dim, mid_dim, hidden) = (1 * 28 * 28, args.mid_dim, args.hidden)
        transform = torchvision.transforms.ToTensor()
        trainset = torchvision.datasets.FashionMNIST(root='~/torch/data/FashionMNIST',
                                                     train=True, download=True, transform=transform)
        trainloader = torch.utils.data.DataLoader(trainset,
                                                  batch_size=batch_size, shuffle=True, num_workers=2)
        testset = torchvision.datasets.MNIST(root='./data/FashionMNIST',
                                             train=False, download=True, transform=transform)
        testloader = torch.utils.data.DataLoader(testset,
                                             batch_size=args.batch_size, shuffle=False, num_workers=1)
    if latent == 'normal':
        prior = torch.distributions.Normal(
            torch.tensor(0.).to(device), torch.tensor(1.).to(device))
    elif latent == 'logistic':
        prior = utils.StandardLogistic()

    model_save_filename = '%s_' % args.dataset \
                          + 'batch%d_' % args.batch_size \
                          + 'coupling%d_' % args.coupling \
                          + 'mid%d_' % args.mid_dim \
                          + 'hidden%d_' % args.hidden \
                          + '.pt'

    flow = nice.NICE(prior=prior,
                     coupling=coupling,
                     in_out_dim=full_dim,
                     mid_dim=mid_dim,
                     hidden=hidden,
                     mask_config=mask_config,
                     coup_type=args.coup_type).to(device)
    optimizer = torch.optim.Adam(
        flow.parameters(), lr=lr, betas=(momentum, decay), eps=1e-4)

    train_loss = []
    test_loss  = []
    for e in range(args.max_iter):
        train_loss.append(train(flow, trainloader, optimizer, device, args.dataset))
        test_loss.append(test(flow, testloader, e, device=device,
                              dataset=args.dataset,filename=f"{args.dataset}_sampled"))
        if e % args.save_every == 0:
            torch.save(flow.state_dict(), "./models/"+model_save_filename)
            print(f"Epoch {e}:  train loss: {train_loss[-1]} ")

    fig, ax = plt.subplots()
    ax.plot(train_loss)
    ax.plot(test_loss)
    ax.set_title("Train/Test LL Loss")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss")
    ax.legend(["train loss","test loss"])
    # ax.legend(["train loss"])
    plt.savefig(os.path.join(os.getcwd(),"loss",f"{args.dataset}_loss.png"))

if __name__ == '__main__':
    parser = argparse.ArgumentParser('MNIST NICE PyTorch implementation')
    parser.add_argument('--dataset',
                        help='dataset to be modeled.',
                        type=str,
                        default='mnist')
    parser.add_argument('--batch_size',
                        help='number of images in a mini-batch.',
                        type=int,
                        default=200)
    parser.add_argument('--latent',
                        help='latent distribution.',
                        type=str,
                        default='logistic')
    parser.add_argument('--max_iter',
                        help='maximum number of iterations.',
                        type=int,
                        default=50)
    parser.add_argument('--sample_size',
                        help='number of images to generate.',
                        type=int,
                        default=64)
    parser.add_argument('--lr',
                        help='initial learning rate.',
                        type=float,
                        default=1e-3)
    parser.add_argument('--momentum',
                        help='beta1 in Adam optimizer.',
                        type=float,
                        default=0.9)
    parser.add_argument('--decay',
                        help='beta2 in Adam optimizer.',
                        type=float,
                        default=0.999)
    parser.add_argument('--coupling',
                        help='.',
                        type=int,
                        default=4)
    parser.add_argument('--save-every',
                        help='every how many epochs to save the model',
                        type=float,
                        default=10)
    parser.add_argument('--coup-type',
                        help="coupling type",
                        type=str,
                        default="additive")
    parser.add_argument('--mid-dim',
                        help='.',
                        type=int,
                        default=1000)
    parser.add_argument('--hidden',
                        help='.',
                        type=int,
                        default=5)

    args = parser.parse_args()
    main(args)
