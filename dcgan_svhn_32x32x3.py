import tensorflow as tf
from utils.load_tfrecords_32x32x3 import *
import numpy as np
import math

batch_size = 128

statis   = lambda x: tf.nn.moments(x,axes=[0,1,2])
bn       = lambda x: tf.nn.batch_normalization(x,statis(x)[0],statis(x)[1],None,None,1e-5)
bn_relu  = lambda x: tf.nn.relu(bn(x))
bn_lrelu = lambda x: tf.maximum(0.2*bn(x),bn(x))

#x.shape = [-1,32,32,3] y.shape=[-1,10] z.shape=[-1,100]
Z = tf.placeholder(tf.float32,shape=[None,100])

#dconv1.shape = [128,4,4,512]
w_dconv1 = tf.Variable(tf.truncated_normal([100,512*4*4],stddev=0.1),name='G_w_dconv1')
b_dconv1 = tf.Variable(tf.constant(0.1,shape=[512]),name='G_b_dconv1')
dconv1   = bn_relu(tf.reshape(tf.matmul(Z,w_dconv1),[-1,4,4,512])+b_dconv1)

#dconv2.shape = [-1,8,8,256]
w_dconv2 = tf.Variable(tf.truncated_normal([5,5,256,512],stddev=0.1),name='G_w_dconv2')
b_dconv2 = tf.Variable(tf.constant(0.1,shape=[256]),name='G_b_dconv2')
dconv2   = bn_relu(tf.nn.conv2d_transpose(dconv1,w_dconv2,[batch_size,8,8,256],strides=[1,2,2,1])+b_dconv2)

#dconv3.shape = [-1,16,16,128]
w_dconv3 = tf.Variable(tf.truncated_normal([5,5,128,256],stddev=0.1),name='G_w_dconv3')
b_dconv3 = tf.Variable(tf.constant(0.1,shape=[128]),name='G_b_dconv3')
dconv3   = bn_relu(tf.nn.conv2d_transpose(dconv2,w_dconv3,[batch_size,16,16,128],strides=[1,2,2,1])+b_dconv3)


#dconv3.shape = [-1,32,32,3]
w_dconv4 = tf.Variable(tf.truncated_normal([5,5,3,128],stddev=0.1),name='G_w_dconv4')
b_dconv4 = tf.Variable(tf.constant(0.1,shape=[3]),name='G_b_dconv4')
G        = tf.nn.tanh(tf.nn.conv2d_transpose(dconv3,w_dconv4,[batch_size,32,32,3],strides=[1,2,2,1])+b_dconv4)

X = tf.placeholder(tf.float32,shape=[None,32,32,3])

#conv1.shape=[-1, , 64],  strides=[1,2,2,1]
w_conv1 = tf.Variable(tf.truncated_normal([5,5,3,64],stddev=0.1),name='D_w_conv1')
b_conv1 = tf.Variable(tf.constant(0.1,shape=[64]),name='D_b_conv1')
X_conv1 = bn_lrelu(tf.nn.conv2d(X, w_conv1, strides=[1,2,2,1], padding='SAME')+b_conv1)
G_conv1 = bn_lrelu(tf.nn.conv2d(G, w_conv1, strides=[1,2,2,1], padding='SAME')+b_conv1)
#conv1.get_shape=[-1,16,16,64]
#conv2.shape=[-1, , 128], strides=[1,2,2,1]
w_conv2 = tf.Variable(tf.truncated_normal([5,5,64,128],stddev=0.1),name='D_w_conv2')
b_conv2 = tf.Variable(tf.constant(0.1,shape=[128]),name='D_b_conv2')
X_conv2 = bn_lrelu(tf.nn.conv2d(X_conv1, w_conv2, strides=[1,2,2,1],padding='SAME')+b_conv2)
G_conv2 = bn_lrelu(tf.nn.conv2d(G_conv1, w_conv2, strides=[1,2,2,1],padding='SAME')+b_conv2)
#conv2.get_shape=[-1,8,8,128]
#conv3.shape=[-1, , 256], strides=[1,2,2,1]
w_conv3 = tf.Variable(tf.truncated_normal([5,5,128,256],stddev=0.1),name='D_w_conv3')
b_conv3 = tf.Variable(tf.constant(0.1,shape=[256]),name='D_b_conv3')
X_conv3 = bn_lrelu(tf.nn.conv2d(X_conv2, w_conv3, strides=[1,2,2,1], padding='SAME')+b_conv3)
G_conv3 = bn_lrelu(tf.nn.conv2d(G_conv2, w_conv3, strides=[1,2,2,1], padding='SAME')+b_conv3)
#conv3.get_shape=[-1,4,4,256]
#fc1.shape => 1
X_conv3_flat = tf.reshape(X_conv3,shape=[-1,4*4*256])
G_conv3_flat = tf.reshape(G_conv3,shape=[-1,4*4*256])
w_fc1   = tf.Variable(tf.truncated_normal([4*4*256,1],stddev=0.1),name='D_w_fc1')
b_fc1   = tf.Variable(tf.constant(0.1,shape=[1]),name='D_b_fc1')
DX      = tf.sigmoid(tf.matmul(X_conv3_flat,w_fc1)+b_fc1)
DG      = tf.sigmoid(tf.matmul(G_conv3_flat,w_fc1)+b_fc1)

Dloss   = -tf.reduce_mean(tf.log(DX)  + tf.log(1-DG))
Gloss   =  tf.reduce_mean(tf.log(1-DG)- tf.log(DG+1e-6))
#Dloss   = -tf.reduce_mean(DX-DG)
#Gloss   = -tf.reduce_mean(DG)
Dvars   = [v for v in tf.trainable_variables() if v.name.startswith('D')]
Gvars   = [v for v in tf.trainable_variables() if v.name.startswith('G')]
trainD  = tf.train.AdamOptimizer(1e-3).minimize(Dloss, var_list=Dvars)
trainG  = tf.train.AdamOptimizer(1e-3).minimize(Gloss, var_list=Gvars)

tr_img, tr_label = load_tfrecords('svhn/train.tfrecords')
ts_img, ts_label = load_tfrecords('svhn/test.tfrecords')

tr_batch_img, tr_batch_label = tf.train.shuffle_batch([tr_img, tr_label], batch_size=batch_size,capacity=3000,min_after_dequeue=100)
ts_batch_img, ts_batch_label = tf.train.shuffle_batch([ts_img, ts_label], batch_size=batch_size,capacity=3000,min_after_dequeue=100)


sess = tf.Session()
sess.run(tf.global_variables_initializer())
theards = tf.train.start_queue_runners(sess=sess)

#print('loading data')
#tr_batch = sess.run([tr_batch_img, tr_batch_label])
#ts_batch = sess.run([ts_batch_img, ts_batch_label])
#print tr_batch[0].shape,tr_batch[1].shape
#print ts_batch[0].shape,ts_batch[1].shape
#print('Done!')
ndloss=ngloss=0.0
for i in range(20000):
    z = np.random.uniform(-1,1,size=(batch_size,100))
    tr_batch = sess.run([tr_batch_img, tr_batch_label])
    #print z.shape,type(z)
    dloss,_ = sess.run([Dloss,trainD],feed_dict={X:tr_batch[0],Z:z})
    ndloss += dloss
    print(str(i)+'dloss:'+str(dloss)+'/'+str(ndloss))
    z = np.random.uniform(-1,1,size=(batch_size,100))
    gloss,_ = sess.run([Gloss,trainG],feed_dict={Z:z})
    ngloss += gloss
    print(str(i)+'gloss:'+str(gloss)+'/'+str(ngloss))

    if  math.isnan(ndloss) or math.isnan(ngloss) or ngloss>1000:
        print('...initialize parameters for nan...')
        sess.run(tf.global_variables_initializer())
        ndloss=ngloss=0.0

#import matplotlib.pyplot as plt
#import numpy as np
#g = sess.run(G,feed_dict={Z:z})
#fig = plt.gcf()
#fig.subplots_adjust(left=0,bottom=0,right=1,top=1)
#for i in range(batch_size):
#      ax = fig.add_subplot(10, np.ceil(batch_size/10.0), i + 1)
#      ax.axis("off")
#      ax.imshow(g[i,:,:,:])
#plt.savefig('.')
#plt.draw()
#plt.pause(0.01)





