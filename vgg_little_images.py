def new_dataset():
    img_list = os.listdir('./shrunken_images')

    images = np.empty((594, 32, 32, 3), dtype=np.uint8)
    labels = np.empty((594), dtype=np.uint8)

    i = 0

    for image in img_list:
        img = cv2.imread('./shrunken_images/' + image)
        #images[i] = img.transpose(2, 0, 1)
        images[i] = img
        name = image.split('.')[0]
        labels[i] = name.split('_')[-1]
        i += 1
    train_data = images[:416]
    train_labels = labels[:416]
    test_data = images[416:]
    test_labels = labels[416:]

    return train_data, utils._dense_to_one_hot(train_labels, 3), test_data, utils._dense_to_one_hot(test_labels, 3)

class Hyperparameters:
    def __init__(self):
        self.image_size = 32
        self.image_channels = 3
        self.num_classes = 3
        self.initial_learning_rate = 1e-4
        self.decay_steps = 1e3
        self.decay_rate = 0.98
        self.cut_layer = "pool5"
        self.hidden_layers = [512]
        self.batch_size = 128
        self.num_epochs = 200
        self.check_points_path= "./tensorboard/atypia"
        self.keep = 1.0
        self.fine_tunning = False
        self.bottleneck = True
    
class utils:
    def get_or_generate_bottleneck( sess, model, file_name, dataset, labels, batch_size = 128):

        path_file = os.path.join("./data_set",file_name+".pkl")
        if(os.path.exists(path_file)):
            print("Loading bottleneck from \"{}\" ".format(path_file))
            with open(path_file, 'rb') as f:
                return pickle.load(f)

        bottleneck_data = []
        original_labels = []

        print("Generating Bottleneck \"{}.pkl\" ".format(file_name) )
        count = 0
        amount = len(labels) // batch_size
        indices = list(range(len(labels)))
        for i in range(amount+1):

            if (i+1)*batch_size < len(indices):
                indices_next_batch = indices[i*batch_size: (i+1)*batch_size]
            else:
                indices_next_batch = indices[i*batch_size:]
            batch_size = len(indices_next_batch)

            data = dataset[indices_next_batch]
            label = labels[indices_next_batch]
            input_size = np.prod(model["bottleneck_tensor"].shape.as_list()[1:])
            tensor = sess.run(model["bottleneck_tensor"], feed_dict={model["images"]:data, model["bottleneck_input"]:np.zeros((batch_size,input_size)), model["labels"]:label,model["keep"]:1.0})
            for t in range(batch_size):
                bottleneck_data.append(np.squeeze(tensor[t]))
                original_labels.append(np.squeeze(label[t]))

        bottleneck = {
            "data":np.array(bottleneck_data),
            "labels":np.array(original_labels)
        } 

        with open(path_file, 'wb') as f:
            pickle.dump(bottleneck, f)
        print("Done")   

        return bottleneck



    def get_data_set(name="train"):
        x = None
        y = None
        folder_name = 'cifar_10'
        main_directory = "./data_set"
        url = "http://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz"

        utils.maybe_download_and_extract(url, main_directory,folder_name, "cifar-10-batches-py")


        f = open(os.path.join(main_directory,folder_name,"batches.meta"), 'rb')
        f.close()

        if name is "train":
            for i in range(5):
                f = open('./data_set/'+folder_name+'/data_batch_' + str(i + 1), 'rb')
                datadict = pickle.load(f, encoding='latin1')
                f.close()

                _X = datadict["data"]
                _Y = datadict['labels']

                _X = np.array(_X, dtype=float) / 255.0
                _X = _X.reshape([-1, 3, 32, 32])
                _X = _X.transpose([0, 2, 3, 1])

                if x is None:
                    x = _X
                    y = _Y
                else:
                    x = np.concatenate((x, _X), axis=0)
                    y = np.concatenate((y, _Y), axis=0)

        elif name is "test":
            f = open('./data_set/'+folder_name+'/test_batch', 'rb')
            datadict = pickle.load(f, encoding='latin1')
            f.close()

            x = datadict["data"]
            y = np.array(datadict['labels'])

            x = np.array(x, dtype=float) / 255.0
            x = x.reshape([-1, 3, 32, 32])
            x = x.transpose([0, 2, 3, 1])

        return x, utils._dense_to_one_hot(y)


    def _dense_to_one_hot( labels_dense, num_classes=10):
        num_labels = labels_dense.shape[0]
        index_offset = np.arange(num_labels) * num_classes
        labels_one_hot = np.zeros((num_labels, num_classes))
        labels_one_hot.flat[index_offset + labels_dense.ravel()] = 1

        return labels_one_hot

    def maybe_download_and_extract( url, main_directory,filename, original_name):
        def _print_download_progress( count, block_size, total_size):
            pct_complete = float(count * block_size) / total_size
            msg = "\r --> progress: {0:.1%}".format(pct_complete)
            sys.stdout.write(msg)
            sys.stdout.flush()

        if not os.path.exists(main_directory):
            os.makedirs(main_directory)
            url_file_name = url.split('/')[-1]
            zip_file = os.path.join(main_directory,url_file_name)
            print("Downloading ",url_file_name)

            try:
                file_path, _ = urlretrieve(url=url, filename= zip_file, reporthook=_print_download_progress)
            except:
                os.system("rm -r "+main_directory)
                print("An error occurred while downloading: ",url)

                if(original_name == 'vgg16-20160129.tfmodel'):
                    print("This could be for a problem with github. We will try downloading from the Google Drive")
                    from google_drive_downloader import GoogleDriveDownloader as gdd

                    gdd.download_file_from_google_drive(file_id='1xJZDLu_TK_SyQz-SaetAL_VOFY7xdAt5',
                                                        dest_path='./models/vgg16-20160129.tfmodel',
                                                        unzip=False)
                else: print("This could be for a problem with the storage site. Try again later")
                return

            print("\nDownload finished.")
            if file_path.endswith(".zip"):
                print( "Extracting files.")

                zipfile.ZipFile(file=file_path, mode="r").extractall(main_directory)
            elif file_path.endswith((".tar.gz", ".tgz")):
                print( "Extracting files.")
                tarfile.open(name=file_path, mode="r:gz").extractall(main_directory)
                os.remove(file_path)

            os.rename(os.path.join(main_directory,original_name), os.path.join(main_directory,filename))
            print("Done.")

    def data_augmentation(images, labels):

        def random_rotation(image_array):
            random_degree = random.uniform(-15, 15)
            return sk.transform.rotate(image_array, random_degree)

        def random_noise(image_array):
            return sk.util.random_noise(image_array)

        def horizontal_flip(image_array):
            return image_array[:, ::-1]

        print("Augmenting data...")
        aug_images = []
        aug_labels = []

        aug_images.extend( list(map(random_rotation, images)) )
        aug_labels.extend(labels)
        aug_images.extend( list(map(random_noise,    images)) )
        aug_labels.extend(labels)
        aug_images.extend( list(map(horizontal_flip, images)) )
        aug_labels.extend(labels)


        return np.array(aug_images), np.array(aug_labels)


    def generate_confusion_matrix( predictions, class_names):

        def plot_confusion_matrix(cm, classes,
                                  normalize=False,
                                  title='Confusion matrix',
                                  cmap=plt.cm.Blues):
            """
            This function prints and plots the confusion matrix.
            Normalization can be applied by setting `normalize=True`.
            """
            if normalize:
                cm = 100 * cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
                print("Normalized confusion matrix")
            else:
                print('Confusion matrix, without normalization')

            print(cm.shape)

            plt.imshow(cm, interpolation='nearest', cmap=cmap)
            plt.title(title)
            plt.colorbar()

            tick_marks = np.arange(len(classes))


            plt.xticks(tick_marks, classes, rotation=45)
            plt.yticks(tick_marks, classes)

            fmt = '.2f' if normalize else 'd'
            thresh = cm.max() / 2.
            symbol = "%" if normalize else ""
            for i, j in product(range(cm.shape[0]), range(cm.shape[1])):
                plt.text(j, i, format(cm[i, j], fmt)+symbol,
                         horizontalalignment="center",
                         color="white" if cm[i, j] > thresh else "black")

            plt.tight_layout()
            plt.ylabel('Real')
            plt.xlabel('Predicted')

        # Compute confusion matrix
        cnf_matrix = confusion_matrix(predictions["labels"],predictions["classes"])
        np.set_printoptions(precision=2)

        # # Plot normalized confusion matrix
        plt.figure(figsize=(10,7))
        plot_confusion_matrix(cnf_matrix, classes=class_names, normalize=True,
                              title='Normalized confusion matrix')
        plt.grid('off')

        #plt.savefig("./confusion_matrix.png") #Save the confision matrix as a .png figure.
        plt.show()
      
def get_vgg16(input_images, cut_layer = "pool5", scope_name = "vgg16", fine_tunning = False):  

    file_name = 'vgg16-20160129.tfmodel'
    main_directory = "./models/"
    vgg_path = os.path.join(main_directory,file_name)
    if not os.path.exists(vgg_path):
        vgg16_url = "https://media.githubusercontent.com/media/pavelgonchar/colornet/master/vgg/tensorflow-vgg16/vgg16-20160129.tfmodel"
        utils.maybe_download_and_extract(vgg16_url, main_directory, file_name, file_name)


    with open(vgg_path, mode='rb') as f:
        content = f.read()
        graph_def = tf.GraphDef()
        graph_def.ParseFromString(content)
        graph_def = tf.graph_util.extract_sub_graph(graph_def, ["images", cut_layer])
        tf.import_graph_def(graph_def, input_map={"images": input_images})
    del content

    graph = tf.get_default_graph()
    vgg_node = "import/{}:0".format(cut_layer) #It is possible to cut the graph in other node. 
                                                #For this, it is necessary to see the name of all layers by using the method 
                                                #"get_operations()": "print(graph.get_operations())" 


    vgg_trained_model = graph.get_tensor_by_name("{}/{}".format(scope_name, vgg_node) )

    if not fine_tunning:
        print("Stopping gradient")
        vgg_trained_model = tf.stop_gradient(vgg_trained_model) #Just use it in case of transfer learning without fine tunning


   #   print(graph.get_operations())
    return vgg_trained_model, graph
  
def transfer_learning_model(params = None, fine_tunning = False, bottleneck = False):
   
    if params is None:
        params = Hyperparameters()
      
    with tf.name_scope('placeholders_variables'):
        input_images = tf.placeholder(tf.float32, shape=[None,params.image_size, params.image_size, params.image_channels], name='input')
        labels = tf.placeholder(tf.float32, shape=[None, params.num_classes], name='labels')
#         reshaped_images = tf.reshape(input_images, [-1, params.image_size, params.image_size, params.image_channels], name='images')
        dropout_keep  =  tf.placeholder(tf.float32, name='dropout_keep')
        global_step = tf.train.get_or_create_global_step()
        learning_rate = tf.train.exponential_decay(params.initial_learning_rate, global_step, 
                                                   params.decay_steps,params.decay_rate, staircase=True)       
    

    with tf.name_scope('vgg16'):
     # Create a VGG16 model and reuse its weights.
        vgg16_out,_ = get_vgg16(input_images=input_images,cut_layer = params.cut_layer, fine_tunning = fine_tunning)
      
    with tf.name_scope("flatten"):
        flatten = tf.layers.flatten(vgg16_out, name="flatten")
    
    if (not fine_tunning) and bottleneck:
        out_list = flatten.shape.as_list()
        BOTTLENECK_TENSOR_SIZE = np.prod(out_list[1:]) # All input layer size, less the batch size
        with tf.name_scope('bottleneck'):
            bottleneck_tensor = flatten
            bottleneck_input = tf.placeholder(tf.float32,
            shape=[None, BOTTLENECK_TENSOR_SIZE],
            name='InputPlaceholder')

        with tf.name_scope('fully_conn'):
            logits = fc_model(bottleneck_input, params.hidden_layers) #Create a fully connected model that will be feed by the bottleneck
    
    else:
        with tf.name_scope('fully_conn'):
            logits = fc_model(flatten, params.hidden_layers) #Create a fully connected model that will be feed by the vgg16

        

    with tf.name_scope('loss'):
        loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits_v2(logits=logits, labels=labels))
#         loss = regularize(loss)
        tf.summary.scalar("loss", loss)


    with tf.name_scope('sgd'):
        update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
        with tf.control_dependencies(update_ops):
            optimizer = tf.train.AdamOptimizer(learning_rate).minimize(loss, global_step=global_step)

    with tf.name_scope('train_accuracy'):
        acc = tf.equal(tf.argmax(logits, 1), tf.argmax(labels, 1))
        acc = tf.reduce_mean(tf.cast(acc, tf.float32))
        tf.summary.scalar("accuracy", acc)
   
    
    predictions = {
                   "classes": tf.argmax(logits, 1),
                   "probs" :  tf.nn.softmax(logits), 
                   "labels": tf.argmax(labels, 1)
                  }
    model = {
             "global_step": global_step,
             "images": input_images,
             "labels": labels,    
             "loss" : loss,
             "optimizer": optimizer,
             "accuracy": acc,
             "predictions":predictions,
             "keep": dropout_keep
            }

    
    if (not fine_tunning) and bottleneck:
        model.update({"bottleneck_tensor":bottleneck_tensor})
        model.update({"bottleneck_input":bottleneck_input})
     
 
        
    return model
        
def get_fc_weights(w_inputs, w_output, id=0):
    weight= tf.Variable(tf.truncated_normal([w_inputs, w_output]), name="{}/weight".format(id))
    bias =  tf.Variable(tf.truncated_normal([w_output]), name="{}/bias".format(id))
    return weight, bias  

def logits_layer(fc_layer, n_classes):
    out_shape = fc_layer.shape.as_list()
    w, b = get_fc_weights(np.prod(out_shape[1:]), n_classes, "logits/weight")
    logits = tf.add(tf.matmul(fc_layer, w), b, name="logits")
    return logits
      
def fc_layer(input_layer, number_of_units, keep = None, layer_id = "fc"):
    pl_list = input_layer.shape.as_list()
    input_size = np.prod(pl_list[1:])

    w, b = get_fc_weights(input_size, number_of_units, layer_id)  
    fc_layer = tf.matmul(input_layer, w, name="{}/matmul".format(layer_id))
    fc_layer = tf.nn.bias_add(fc_layer, b, name="{}/bias-add".format(layer_id))

    if keep is not None:
        fc_layer = tf.nn.dropout(fc_layer, keep, name="{}/dropout".format(layer_id))
    else:
        print("Dropout was disabled.")

    fc_layer = tf.nn.relu(fc_layer, name="{}/relu".format(layer_id))
    return fc_layer
      
def regularize(loss, type = 1, scale = 0.005, scope = None):
    if type == 1:
        regularizer = tf.contrib.layers.l1_regularizer( scale=scale, scope=scope)
    else:
        regularizer = tf.contrib.layers.l2_regularizer( scale=scale, scope=scope)

    weights = tf.trainable_variables() # all vars of your graph
    regularization_penalty = tf.contrib.layers.apply_regularization(regularizer, weights)
    regularized_loss = loss + regularization_penalty
    return regularized_loss

def fc_model(flatten, hidden_layers = [512], keep = None):
    fc = flatten
    id = 1
    for num_neurons in hidden_layers:
        fc = fc_layer(fc, num_neurons, keep,  "fc{}".format(id) )
        id = id+1

    logits = logits_layer(fc, params.num_classes)
    return logits
  
def create_monitored_session(model,iter_per_epoch, checkpoint_dir):
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True

    sess = tf.train.MonitoredTrainingSession(checkpoint_dir=checkpoint_dir,
                                             save_checkpoint_secs=120,
                                             log_step_count_steps=iter_per_epoch,
                                             save_summaries_steps=iter_per_epoch,
                                             config=config) 
    return sess
    
def test(sess, model,input_data_placeholder, data, labels, batch_size = 128):
    global_accuracy = 0
    predictions = {
                   "classes":[],
                   "probs":[],
                   "labels":[]
                  }

    size = len(data)//batch_size
    indices = list(range(len(data)))

    for i in range(size+1):

        begin = i*batch_size
        end = (i+1)*batch_size
        end = len(data) if end >= len(data) else end

        next_bach_indices = indices[begin:end]
        batch_xs = data[next_bach_indices]
        batch_ys = labels[next_bach_indices]

        pred = sess.run(model["predictions"],
            feed_dict={input_data_placeholder: batch_xs, model["labels"]: batch_ys, model["keep"]:1.0})

        predictions["classes"].extend(pred["classes"])
        predictions["probs"].extend(pred["probs"])
        predictions["labels"].extend(pred["labels"])


    correct = list (map(lambda x,y: 1 if x==y else 0, predictions["labels"] , predictions["classes"]))
    acc = np.mean(correct ) *100

    mes = "--> Test accuracy: {:.2f}% ({}/{})"
    print(mes.format( acc, sum(correct), len(data)))

    return predictions
  
def train(params = None):
    if params is None:
        params = Hyperparameters()

    tf.reset_default_graph()
    
    train_data, train_labels, test_data, test_labels = new_dataset()
    #train_data, train_labels = utils.data_augmentation(train_data, train_labels)

    model = transfer_learning_model(params, params.fine_tunning, params.bottleneck)

    steps_per_epoch = int(math.ceil(len(train_data) /  params.batch_size))
    sess = create_monitored_session(model,steps_per_epoch, params.check_points_path)


    if (not params.fine_tunning) and params.bottleneck:
        indices = list( range(len(train_data)) )
        shuffle(indices)

        shuffled_data = train_data[indices]
        shuffled_labels = train_labels[indices]

        bottleneck_train = utils.get_or_generate_bottleneck(sess, model, "bottleneck_vgg16_{}_train".format(params.cut_layer), shuffled_data, shuffled_labels, params.batch_size)
        bottleneck_test = utils.get_or_generate_bottleneck(sess, model, "bottleneck_vgg16_{}_test".format(params.cut_layer), test_data, test_labels, params.batch_size)


        train_data, train_labels  = bottleneck_train["data"], bottleneck_train["labels"]
        test_data, test_labels = bottleneck_test["data"], bottleneck_test["labels"]
        del bottleneck_train, bottleneck_test


        input_data_placeholder = model["bottleneck_input"]




    else:
        input_data_placeholder = model["images"]



    indices = list( range(len(train_data)) )
    msg = "--> Global step: {:>5} - Last batch acc: {:.2f}% - Batch_loss: {:.4f} - ({:.2f}, {:.2f}) (steps,images)/sec"

    for epoch in range(params.num_epochs):
        start_time = time()

        print("\n*************************************************************")
        print("Epoch {}/{}".format(epoch+1,params.num_epochs))

        shuffle(indices)  
        for s in range(steps_per_epoch):

            indices_next_batch = indices[s *  params.batch_size : (s+1) * params.batch_size]
            batch_data = train_data[indices_next_batch]
            batch_labels = train_labels[indices_next_batch]

            _, batch_loss, batch_acc,step = sess.run(
                [model["optimizer"], model["loss"], model["accuracy"], model["global_step"],],
                feed_dict={input_data_placeholder: batch_data, model["labels"]: batch_labels, model["keep"]:params.keep})

        duration = time() - start_time

        print(msg.format(step,  batch_acc*100, batch_loss, (steps_per_epoch / duration), (steps_per_epoch*params.batch_size / duration) ))


        _ = test(sess, model, input_data_placeholder, test_data, test_labels )

    predictions = test(sess, model, input_data_placeholder, test_data, test_labels )

    sess.close()

    class_names = ['1', '2', '3'] 
    utils.generate_confusion_matrix(predictions, class_names)
    
    return predictions