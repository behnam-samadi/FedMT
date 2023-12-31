import warnings

import torch
import torch.nn as nn


def average_learners_classic(
        learners,
        target_learner,
        weights=None,
        average_params=True,
        average_gradients=False):
    """
    Compute the average of a list of learners_ensemble and store it into learner

    :param learners:
    :type learners: List[Learner]
    :param target_learner:
    :type target_learner: Learner
    :param weights: tensor of the same size as learners_ensemble, having values between 0 and 1, and summing to 1,
                    if None, uniform learners_weights are used
    :param average_params: if set to true the parameters are averaged; default is True
    :param average_gradients: if set to true the gradient are also averaged; default is False
    :type weights: torch.Tensor

    """
    if not average_params and not average_gradients:
        return

    if weights is None:
        n_learners = len(learners)
        weights = (1 / n_learners) * torch.ones(n_learners, device=learners[0].device)

    else:
        weights = weights.to(learners[0].device)

    target_state_dict = target_learner.model.state_dict(keep_vars=True)

    for key in target_state_dict:

        if target_state_dict[key].data.dtype == torch.float32:

            if average_params:
                target_state_dict[key].data.fill_(0.)

            if average_gradients:
                target_state_dict[key].grad = target_state_dict[key].data.clone()
                target_state_dict[key].grad.data.fill_(0.)

            for learner_id, learner in enumerate(learners):
                state_dict = learner.model.state_dict(keep_vars=True)

                if average_params:
                    target_state_dict[key].data += weights[learner_id] * state_dict[key].data.clone()

                if average_gradients:
                    if state_dict[key].grad is not None:
                        target_state_dict[key].grad += weights[learner_id] * state_dict[key].grad.clone()
                    elif state_dict[key].requires_grad:
                        warnings.warn(
                            "trying to average_gradients before back propagation,"
                            " you should set `average_gradients=False`."
                        )

        else:
            # tracked batches
            target_state_dict[key].data.fill_(0)
            for learner_id, learner in enumerate(learners):
                state_dict = learner.model.state_dict()
                target_state_dict[key].data += state_dict[key].data.clone()



def average_learners(
        learners,
        target_learner,
        selected_clients_per_class,
        proposed_method,
        beta_proposed,
        weights=None,
        average_params=True,
        average_gradients=False):
    """
    Compute the average of a list of learners_ensemble and store it into learner

    :param learners:
    :type learners: List[Learner]
    :param target_learner:
    :type target_learner: Learner
    :param weights: tensor of the same size as learners_ensemble, having values between 0 and 1, and summing to 1,
                    if None, uniform learners_weights are used
    :param average_params: if set to true the parameters are averaged; default is True
    :param average_gradients: if set to true the gradient are also averaged; default is False
    :type weights: torch.Tensor

    """
    if not average_params and not average_gradients:
        return

    if weights is None:
        n_learners = len(learners)
        weights = (1 / n_learners) * torch.ones(n_learners, device=learners[0].device)

    else:
        weights = weights.to(learners[0].device)

    target_state_dict = target_learner.model.state_dict(keep_vars=True)
    import numpy as np
    from numpy import dot
    from numpy.linalg import norm
    #np.save("state_dict.npy", target_state_dict.cpu())
    #torch.save(target_state_dict, 'state_dict.pth')
    cos = torch.nn.CosineSimilarity(dim=1)
    for key in target_state_dict:
        if target_state_dict[key].data.dtype == torch.float32:
            if average_params:
                target_state_dict[key].data.fill_(0.)
            if average_gradients:
                target_state_dict[key].grad = target_state_dict[key].data.clone()
                target_state_dict[key].grad.data.fill_(0.)
            cuda0 = torch.device('cuda:0')
            if key=="classifier.1.weight":
              temp_layer = torch.zeros((target_state_dict[key].data.shape[0],target_state_dict[key].data.shape[1] ), device=cuda0)
              for class_num in range(10): #immediate_data
                clients = selected_clients_per_class[class_num]
                outliers = []
                for c in range(len(learners)):
                  if not c in clients:
                    outliers.append(c)
                #computing the weights for selected clients weighs:
                # Step1: computing the nearest selected client for each outlier client:
                all_data = []
                for c in range(len(learners)):
                  temp_c_state_dict = learners[c].model.state_dict(keep_vars = True)
                  all_data.append(temp_c_state_dict[key].data.cpu().numpy()[class_num])
                outlier_centers = {}
                for outlier in outliers:
                  dis_to_clients = []
                  for client in clients:
                    cos_sim = dot(all_data[outlier], all_data[client])/(norm(all_data[outlier])*norm(all_data[client]))
                    dis_to_clients.append(cos_sim)
                  dis_to_clients = np.array(dis_to_clients)
                  outlier_centers[outlier] = np.argmax(dis_to_clients)
                #print(outlier_centers)
                  #outlier_centers.append(np.argmax(dis_to_clients))
                # Step2: computing the projection of each outlier on its corresponding center (selected client)
                #center_weights = np.zeros(len(clients))
                sum_gradient_selecteds = 0
                sum_gradient_outliers = 0
                for i in range(len(learners)):
                  if i in clients:
                    sum_gradient_selecteds += all_data[i]
                  elif i in outliers:
                    outlier_data = all_data[i]
                    center_data = all_data[clients[outlier_centers[i]]]
                    projection_mag = (dot(outlier_data , center_data))/norm(center_data)
                    sum_gradient_outliers += ((projection_mag / norm(center_data)) * center_data)
                temp_sub_layer = torch.zeros(target_state_dict[key].data.shape[1], device=cuda0)
                #temp_sub_layer /= len(clients)                  
                sum_gradient_selecteds /= len(clients)
                sum_gradient_outliers /= len(outliers)
                #print("proposed method: " + proposed_method)
                if proposed_method == "proposed1":
                  sum_gradient = sum_gradient_selecteds
                elif proposed_method == "proposed2":
                  sum_gradient = (sum_gradient_selecteds + sum_gradient_outliers)/2
                elif proposed_method == "proposed3":
                  sum_gradient = (sum_gradient_selecteds + (beta_proposed)*sum_gradient_outliers)/(1+beta_proposed)
                else:
                  print("proppsed method is not specified")
                  exit(0)
                temp_layer[class_num, :] = torch.tensor(sum_gradient)
              target_state_dict[key].data = temp_layer.data.clone()

            elif key == "classifier.1.bias":
                temp_layer = torch.zeros((target_state_dict[key].data.shape[0]), device=cuda0)
                for class_num in range(10): #immediate_data
                  clients = selected_clients_per_class[class_num]
                  #print("clients")
                  #print(clients)
                  #print("where selected")
                  temp_sub_layer = torch.zeros(1, device=cuda0)
                  for client in clients:
                    temp_state_dict = learners[client].model.state_dict(keep_vars = True)
                    temp_sub_layer = temp_sub_layer + temp_state_dict[key].data.clone()[class_num]
                  temp_sub_layer /= len(clients)                  
                  temp_layer[class_num] = temp_sub_layer
                target_state_dict[key].data = temp_layer.data.clone()
            else:
                if average_params:
                    target_state_dict[key].data.fill_(0.)

                if average_gradients:
                    target_state_dict[key].grad = target_state_dict[key].data.clone()
                    target_state_dict[key].grad.data.fill_(0.)

                for learner_id, learner in enumerate(learners):
                    state_dict = learner.model.state_dict(keep_vars=True)

                    if average_params:
                        target_state_dict[key].data += weights[learner_id] * state_dict[key].data.clone()

                    if average_gradients:
                        if state_dict[key].grad is not None:
                            target_state_dict[key].grad += weights[learner_id] * state_dict[key].grad.clone()
                        elif state_dict[key].requires_grad:
                            warnings.warn(
                                "trying to average_gradients before back propagation,"
                                " you should set `average_gradients=False`."
                            )

                  

        else:
            # tracked batches
            target_state_dict[key].data.fill_(0)
            for learner_id, learner in enumerate(learners):
                state_dict = learner.model.state_dict()
                target_state_dict[key].data += state_dict[key].data.clone()

def partial_average(learners, average_learner, alpha):
    """
    performs a step towards aggregation for learners, i.e.

    .. math::
        \forall i,~x_{i}^{k+1} = (1-\alpha) x_{i}^{k} + \alpha \bar{x}^{k}

    :param learners:
    :type learners: List[Learner]
    :param average_learner:
    :type average_learner: Learner
    :param alpha:  expected to be in the range [0, 1]
    :type: float

    """
    source_state_dict = average_learner.model.state_dict()

    target_state_dicts = [learner.model.state_dict() for learner in learners]

    for key in source_state_dict:
        if source_state_dict[key].data.dtype == torch.float32:
            for target_state_dict in target_state_dicts:
                target_state_dict[key].data =\
                    (1-alpha) * target_state_dict[key].data + alpha * source_state_dict[key].data


def differentiate_learner(target, reference_state_dict, coeff=1.):
    """
    set the gradient of the model to be the difference between `target` and `reference` multiplied by `coeff`

    :param target:
    :type target: Learner
    :param reference_state_dict:
    :type reference_state_dict: OrderedDict[str, Tensor]
    :param coeff: default is 1.
    :type: float

    """
    target_state_dict = target.model.state_dict(keep_vars=True)

    for key in target_state_dict:
        if target_state_dict[key].data.dtype == torch.float32:

            target_state_dict[key].grad = \
                coeff * (target_state_dict[key].data.clone() - reference_state_dict[key].data.clone())


def copy_model(target, source):
    """
    Copy learners_weights from target to source
    :param target:
    :type target: nn.Module
    :param source:
    :type source: nn.Module
    :return: None

    """
    target.load_state_dict(source.state_dict())


def simplex_projection(v, s=1):
    """
    Compute the Euclidean projection on a positive simplex
    Solves the optimisation problem (using the algorithm from [1]):

    .. math::
        min_w 0.5 * || w - v ||_2^2,~s.t. \sum_i w_i = s, w_i >= 0

    Parameters
    ----------
    v: (n,) torch tensor,
       n-dimensional vector to project
    s: int, optional, default: 1,
       radius of the simplex

    Returns
    -------
    w: (n,) torch tensor,
       Euclidean projection of v on the simplex

    Notes
    -----
    The complexity of this algorithm is in O(n log(n)) as it involves sorting v.

    References
    ----------
    [1] Wang, Weiran, and Miguel A. Carreira-Perpinán. "Projection
        onto the probability simplex: An efficient algorithm with a
        simple proof, and an application." arXiv preprint
        arXiv:1309.1541 (2013)
        https://arxiv.org/pdf/1309.1541.pdf

    """

    assert s > 0, "Radius s must be strictly positive (%d <= 0)" % s
    n, = v.shape

    u, _ = torch.sort(v, descending=True)

    cssv = torch.cumsum(u, dim=0)

    rho = int(torch.nonzero(u * torch.arange(1, n + 1) > (cssv - s))[-1][0])

    lambda_ = - float(cssv[rho] - s) / (1 + rho)

    w = v + lambda_

    w = (w * (w > 0)).clip(min=0)

    return w