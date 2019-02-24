import torch
import torch.nn as nn
from HyperParameters import options

'''
General Soft-Attention Model
'''
class Attention(nn.Module):
    '''
        Attention parameters:
            c_size: context size
            h_size: query size
        Inputs:
            c_t: context of shape (N,1,c_size)
            h_i: query of shape   (N,S,h_size)
        Formulation:
            score = c_t^T * W_a * q_i
            alpha_ti = exp(score) / sum_{i=1}^{n}{exp(score)}
            s_t = sum_{i=1}^{n}{alpha_ti * q_i}
        General idea:
            create a score for the current context at time t for every query i
            use the scores to create importance probabilites for every query i
            save the importance probabilities as the attention weights
            scale each query i by its importance
            sum the weighted queries together to produce the summary s_t
    '''
    def __init__(self, q_size, c_size):
        super(Attention,self).__init__()
        self.q_size = q_size
        self.c_size = c_size
        self.W_a = nn.Linear(self.q_size, self.c_size, bias=False)
        self.softmax = nn.Softmax(1)
    def forward(self,q,c_t):
        if c_t is None:
            c_t = q.new_zeros(q.size(0), 1, self.c_size)
        W_attn = self.softmax(self.score(q,c_t))
        alpha_t = W_attn.transpose(1,2)
        s_t = torch.bmm(alpha_t,q)
        return s_t, W_attn
    def score(self,q,c_t):
        return torch.bmm(self.W_a(q),c_t.transpose(1,2))


class Autoencoder(nn.Module):
    def __init__(self):
        super(Autoencoder, self).__init__()
        self.num_epochs = options['n_batches']
        self.LR = options["learning_rate"]
        self.batch_size = options["batch_size"]
        self.hidden_size = options['hidden_neurons']

        self.encoder = nn.Sequential(
            nn.Conv2d(3, 16, 3, stride=3, padding=1),
            nn.ReLU(True),
            nn.MaxPool2d(2, stride=2),
            nn.Conv2d(16, 8, 3, stride=2, padding=1),
            nn.ReLU(True),
            nn.MaxPool2d(2, stride=1),
            nn.Conv2d(8, 4, 3,stride=2,padding=1),
            nn.ReLU(True)
        )
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(4, 8, 1, stride=2),
            nn.ReLU(True),
            nn.ConvTranspose2d(8, 16, 3, stride=2),
            nn.ReLU(True),
            nn.ConvTranspose2d(16, 8, 5, stride=3, padding=1),
            nn.ReLU(True),
            nn.ConvTranspose2d(8, 3, (2,2), stride=2, padding=1),
            nn.Tanh()
        )
        self.criterion = nn.MSELoss()
        self.optimizer = torch.optim.Adam(self.parameters(), lr=self.LR,
                                          weight_decay=1e-5)
    def forward(self, x):
        x = self.encoder(x)
        x = self.decoder(x)
        return x


class ImageEncoder(nn.Module):
    def __init__(self):
        super(ImageEncoder,self).__init__()
        self.num_epochs = options['n_batches']
        self.LR = options["learning_rate"]
        self.batch_size = options["batch_size"]
        self.hidden_size = options['hidden_neurons']
        self.vocab_size = options['vocab_size']

        self.conv = nn.Sequential(
            nn.Conv2d(3, 48, 3, stride=3, padding=1),
            nn.ReLU(True),
            nn.MaxPool2d(2, stride=2),
            nn.Conv2d(48, 18, 5, stride=1),
            nn.ReLU(True),
            nn.MaxPool2d(2, stride=1),
            nn.Conv2d(18, 25, 5, stride=1),
            nn.ReLU(True),
            nn.MaxPool2d(2, stride=1),
            nn.Conv2d(25, 100, 3, stride=1),
            nn.ReLU(True),
            nn.MaxPool2d(2, stride=1),
            nn.ReLU(True),
        )
        self.attention = Attention(100,100)
        self.rnn = nn.GRU(100,100,1,batch_first=True)

        self.criterion = nn.MSELoss()
        self.optimizer = torch.optim.Adam(self.parameters(), lr=self.LR,
                                          weight_decay=1e-5)
    def forward(self, x, num):
        x = self.conv(x).transpose(1,3).contiguous().view(self.batch_size,-1,100)
        hn = None
        y = torch.empty((self.batch_size,num,100))
        for i in range(num):
            x,x_weights = self.attention(x,hn)
            if hn is not None:
                hn = hn.transpose(0,1)
            x,hn = self.rnn(x,hn)
            y[:,i,:] = x.squeeze(1)
            hn = hn.transpose(0,1)
        return y