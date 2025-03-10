from functools import partialmethod

import numpy as np 

class Tensor:
  def __init__(self, data): 
    if type(data) != np.ndarray: 
      print("data should be type of ndarray")
      assert(False)
      
    self.data = data
    self.grad = None

    self._ctx = None

  def __str__(self): 
    return "Tensor %r with grad %r" % (self.data, self.grad)

  def backward(self, allow_fill=True):
    if self._ctx is None:
      return 
    
    if self.grad is None and allow_fill:
      assert self.data.size == 1 
      self.grad = np.ones_like(self.data)
    
    assert(self.grad is not None)

    # print("we are doing backward for tensor with shape", self.data.shape, allow_fill)
    
    grads = self._ctx.backward(self._ctx, self.grad)
    if len(self._ctx.parents) == 1: 
      grads = [grads]
    for t, g in zip(self._ctx.parents, grads): 
      # print("we are doing backward for pareeeeeeeents with shape", g.shape, t.data.shape, len(self._ctx.parents))

      if g.shape != t.data.shape: 
        print("grad shape must match tensor shape in %r, %r != %r" %
          (self._ctx, g.shape, t.data.shape))
        assert(False)
      t.grad = g
      t.backward(False)

  def mean(self):
    div = Tensor(np.array([1/self.data.size]))
    return self.sum().mul(div)

# base class for any operator
class Function: 
  def __init__(self, *tensors): 
    self.parents = tensors 
    self.saved_tensors = []

  def save_for_backward(self, *x):
    self.saved_tensors.extend(x)

  def apply(self, arg, *x): 
    ctx = arg(self, *x)
    ret = Tensor(arg.forward(ctx, self.data, *[t.data for t in x]))
    # print("apply funciton ", ret.data.shape)
    ret._ctx = ctx 
    return ret 

def register(name, fxn): 
  setattr(Tensor, name, partialmethod(fxn.apply, fxn))

class Mul(Function): 
  @staticmethod
  def forward(ctx, x, y): 
    ctx.save_for_backward(x, y)
    return x*y 

  @staticmethod
  def backward(ctx, grad_output): 
    x, y = ctx.saved_tensors
    return y*grad_output, x*grad_output
register('mul', Mul)

class Add(Function): 
  @staticmethod
  def forward(ctx, x, y): 
    return x+y

  @staticmethod
  def backward(ctx, grad_output): 
    # print("this is add backward, ", grad_output.shape)
    return grad_output, grad_output
register('add', Add)

class ReLU(Function): 
  @staticmethod
  def forward(ctx, input): 
    ctx.save_for_backward(input)
    return np.maximum(input, 0)

  @staticmethod
  def backward(ctx, grad_output): 
    input, = ctx.saved_tensors
    grad_input = grad_output.copy()
    grad_input[input < 0] = 0
    return grad_input 
register('relu', ReLU)

class Dot(Function): 
  @staticmethod
  def forward(ctx, input, weight): 
    ctx.save_for_backward(input, weight)
    return input.dot(weight)

  @staticmethod
  def backward(ctx, grad_output): 
    input, weight = ctx.saved_tensors 
    grad_input = grad_output.dot(weight.T)
    grad_weight = grad_output.T.dot(input).T
    return grad_input, grad_weight
register('dot', Dot)

class Sum(Function):
  @staticmethod
  def forward(ctx, input):
    ctx.save_for_backward(input)
    # print("this is sum function, ", np.array([input.sum()]).shape)
    return np.array([input.sum()])

  @staticmethod
  def backward(ctx, grad_output):
    input, = ctx.saved_tensors
    return grad_output * np.ones_like(input)
register('sum', Sum)

class LogSoftmax(Function):
  @staticmethod
  def forward(ctx, input):
    def logsumexp(x):
      #return np.log(np.exp(x).sum(axis=1))
      c = x.max(axis=1)
      return c + np.log(np.exp(x-c.reshape((-1, 1))).sum(axis=1))
    output = input - logsumexp(input).reshape((-1, 1))
    ctx.save_for_backward(output)
    return output

  @staticmethod
  def backward(ctx, grad_output):
    output, = ctx.saved_tensors
    return grad_output - np.exp(output)*grad_output.sum(axis=1).reshape((-1, 1))
register('logsoftmax', LogSoftmax)
