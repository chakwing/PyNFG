# -*- coding: utf-8 -*-
"""
Implements the DecisionNode class

Part of: PyNFG - a Python package for modeling and solving Network Form Games

Created on Mon Feb 18 10:31:17 2013

Copyright (C) 2013 James Bono (jwbono@gmail.com)

GNU Affero General Public License

"""

from __future__ import division
import numpy as np
import scipy as sp
import scipy.stats.distributions as randvars
from node import *

class DecisionNode(Node):
    """Implements a decision node of the semi-NFG formalism by D. Wolpert
    
    The :class:`classes.DecisionNode` can be initialized with either a 
    conditional probability distribution (CPT) or a distribution object 
    from :py:mod:`scipy.stats.distributions` (discrete and continuous types 
    are both supported).
    
    :arg name: the name of the DecisionNode, usually descriptive, e.g. D5, 
       for player 5's decision node, or D51 for player 5's 1st decision node, 
       or D512 for player 5's 1st decision node in the 2nd time step, etc.
    :type name: str
    :arg player: the name of the player to which this DecisionNode belongs.
    :type player: str
    :arg space: the list of the possible values for the DecisionNode. The 
       order determines the order of the CPT when generated.
    :type space: list
    :arg parents: the list of the parents of the decision node. All entries 
       must be a :class:`classes.DecisionNode` or a discrete 
       :class:`classes.ChanceNode` or :class:`nodes.DeterNode`. The order of the 
       parents in the list determinesthe rder of the CPT when generated.
    :type parents: list
    :arg description: a description of the decision node, usually including 
       a summary description of the space, parents and children.
    :type description: str
    :arg time: the timestep to which the node belongs. This is generally 
       only used for :class:`seminfg.iterSemiNFG` objects.
    :type time: int
    :arg basename:  Reference to a theoretical node in the base or kernel.
    :type basename: str
    
    Formally, a decision node has the following properties:
        
       * belongs to a human player
       * has a space of possible values.
       * the conditional probability distribution from the values of its 
          parents - given by :py:meth:`classes.DecisionNode.prob()` or
          :py:meth:`classes.ChanceNode.prob()`, is not specified in the game. 
          That distribution is given by the solution concept applied to the 
          semi-NFG. This lack of CPDs at decision nodes is the reason the 
          semi-NFG is said to be based on a semi-Bayes net.

    .. note::
           
       For a :class:`classes.DecisionNode`, the parents nodes must be 
       discrete.
    
    Example::
        
        import scipy.stats.distributions as randvars
                        
        dist1 = randvars.randint
        params1 = [1, 4]
        space1 = [1, 2, 3]
        distip1 = (dist1, params1, space1)
        C1 = ChanceNode('C1', distip=distip1, description='root CN given by randint 1 to 4')
                        
        D1 = DecisionNode('D1', '1', [-1, 0, 1], parents=[C1], description='This is a child node of C1')
                            
    Upon initialization, the following private method is called: 
    :py:meth:`classes.DecisionNode._set_parent_dict()`
    
    Some useful methods are:
       
    * :py:meth:`classes.DecisionNode.draw_value()` 
    * :py:meth:`classes.DecisionNode.prob()`
    * :py:meth:`classes.DecisionNode.logprob()`
    * :py:meth:`classes.DecisionNode.randomCPT()`
    * :py:meth:`classes.DecisionNode.perturbCPT()`
        
    """
    def __init__(self, name, player, space, parents=[], \
                 description='no description', time=None, basename=None, \
                 verbose=False):
        if verbose:
            try:
                print 'Name: '+ name + '\nDescription: '+ description + \
                    '\nPlayer: '+player 
            except (AttributeError, TypeError):
                raise AssertionError('name, description, player should be strings')
        self.name = name
        self.description = description
        self.time = time
        self.basename = basename
        self.player = player
        self.space = space
        self.parents = self._set_parent_dict(parents)
        self._createCPT()
        self._check_disc_parents()
        self.value = self.space[0]
        self.continuous = False
        
    def __str__(self):
        return self.name
        
    def _createCPT(self):
        """Create a CPT of the correct size with zeros for the DecisionNode
        
        Uses the order of the parents in the parent list as entered by the user 
        to initialize the DecisionNode object and the sizes of space attributes 
        of the parents to create a :py:func:`numpy.zeros()` array of the 
        appropriate size and shape.
        
        """
        CPT_shape = []
        for par in self.parents:
            CPT_shape.append(len(self.parents[par].space))
        CPT_shape.append(len(self.space))
        self.CPT = np.zeros(CPT_shape)
        
    def draw_value(self, parentinput={}, setvalue=True, mode=False):
        """Draw a value from the :class:`classes.DecisionNode` object
        
        :arg parentinput: Optional. Specify values of the parents at which to 
           draw values using the CPT. Keys are parent names. Values are parent 
           values. To specify values for only a subset of the parents, only 
           enter those parents in the dictionary. If no parent values are 
           specified, then the current values of the parents are used. 
        :type parentinput: dict
        :arg setvalue: (Optional) determines if the random draw replaces
           :py:attr:`classes.DecisionNode.value`. True by default.
        :type setvalue: bool
        :arg mode: draws the modal action
        :type mode: bool
        :returns: an element of :py:attr:`classes.DecisionNode.space`.
        
        .. note::
        
           The values specified in parentinput must correspond to an item in the 
           parent's space attribute.
           
        .. warning::
            
           The CPT is an np.zero array upon initialization. Therefore, one must 
           set the CPT wih :py:meth:`classes.DecisionNode.randomCPT()` or 
           manually before calling this method.
        
        """
        if not self.CPT.any():
            raise AttributeError('CPT for %s is just a zeros array' % self.name)
        ind = []
        valslist = self.dict2list_vals(parentinput)
        indo = self.get_CPTindex(valslist, onlyparents=True)
        if not mode:
            cdf = np.cumsum(self.CPT[indo])
            cutoff = np.random.rand()
            idx = np.nonzero( cdf >= cutoff )[0][0]
        else:
            idx = self.CPT[indo].argmax()
        r = self.space[idx]
        if setvalue:
            self.value = r
            return self.value
        else:
            return r
        
    def randomCPT(self, mixed=False, setCPT=True):
        """Create a random CPT for the :class:`classes.DecisionNode` object
        
        :arg mixed: Optional. Determines whether a mixed CPT, i.e. a CPT that 
           assigns nonzero weight to every value in 
           :py:attr:`classes.DecisionNode.space`, or a pure CPT, i.e. a CPT that 
           assigns probability 1 to a single value in 
           :py:attr:`classes.DecisionNode.space` for each of the parent values.
        :type mixed: bool
        :arg setCPT: Optional. Default is True. Determines whether the 
           :py:attr:`classes.DecisionNode.CPT` attribut is set by the function
        :type setCPT: bool
        :returns: a mixed or pure CPT.
        
        """
        CPTshape = self.CPT.shape        
        shape_last = CPTshape[-1]
        other_dims = CPTshape[0:-1]
        z = np.zeros(CPTshape)
        if mixed is False:
            y = randvars.randint.rvs(0, shape_last, size=other_dims)
            if y.size > 1:
                z.reshape((-1, shape_last))[np.arange(y.size), y.flatten()]=1
            else:
                z.reshape((-1, shape_last))[0, y]=1
        else:
            M = 100000000
            x = randvars.randint.rvs(1, M, size=other_dims+(shape_last-1,))
            y = np.concatenate((np.zeros(other_dims+(1,)), x, \
                                M*np.ones(other_dims+(1,))), axis=-1)
            yy = np.sort(y, axis=-1)
            z = np.diff(yy, axis=-1)/M
        if setCPT:
            self.CPT = z
        else:
            return z
            
    def uniformCPT(self, setCPT=True):
        """Create a uniform CPT for the :class:`classes.DecisionNode` object
        
        :arg setCPT: Optional. Default is True. Determines whether the 
           :py:attr:`classes.DecisionNode.CPT` attribute is set by the function
        :type setCPT: bool
        :returns: a uniform mixed CPT.
        
        """
        z = np.zeros(self.CPT.shape)
        z += 1/(self.CPT.shape[-1])
        if setCPT:
            self.CPT = z
        else:
            return z
        
    def perturbCPT(self, noise, mixed=True, sliver=None, setCPT=True):
        """Create a perturbation of the CPT attribute.
        
        :arg noise: The noise determines the mixture between the current CPT 
           and a random CPT, e.g. `new = self.CPT*(1-noise) + randCPT*noise`. 
           Noise must be a number between 0 and 1.
        :type noise: float
        :arg mixed: Optional. Determines if the perturbation is pure or mixed. 
           If pure, then the perturbed CPT is a pure CPT with some of the pure 
           weights shifted to other values. If mixed, then the perturbed CPT is 
           a mixed CPT with positive weight on all values. 
        :type mixed: bool
        :arg sliver: Optional. Determines the values of the parents for which 
           to perturb the current CPT. Keys are parent names. Values are parent 
           values. If empty, the entire CPT is perturbed. If sliver is nonempty, 
           but specifies values for only a subset of parents, the current values 
           are used for the remaining parents.
        :type sliver: dict
        
        .. warning::
            
           Functionality for pure perturbations is not yet implemented!
        
        """
        if not mixed: #pure CPT
            if not sliver: #perturbing the whole CPT
                shape_last = self.CPT.shape[-1]
                altCPT = self.randomCPT(mixed=False, setCPT=False)
                flat = self.CPT.flatten()
                flatalt = altCPT.flatten()
                steps = len(flat)/shape_last
                for  j in xrange(steps):
                    if np.random.rand() < noise:
                        flat[j*shape_last:(j+1)*shape_last-1] = \
                                        flatalt[j*shape_last:(j+1)*shape_last]
                z = flat.reshape(self.CPT.shape)
        else: #mixed CPT
            randCPT = self.randomCPT(mixed=True, setCPT=False)
            if not sliver: #perturbing the whole thing
                z = self.CPT*(1-noise) + randCPT*noise
            else: #perturbing only sliver
                ind = []
                for par in self.parents:
                    if par in sliver:
                        truth = [(x==sliver[par]).all() for x in \
                                                        self.parents[par].space]
                        ind.append(truth.index(True))
                    else:
                        value = self.parents[par].value
                        truth = [(x==value).all() for x in \
                                                        self.parents[par].space]
                        ind.append(truth.index(True))
                indo = tuple(ind)
                z = self.CPT
                z[indo] = z[indo]*(1-noise) + randCPT[indo]*noise
        if setCPT:
            self.CPT = z
        else:
            return z
        
    def prob(self, parentinput={}, valueinput=None):
        """Compute the conditional probability of the current or specified value
        
        :arg parentinput: Optional. Specify values of the parents at which to 
           compute the conditional probability. Keys are parent names. Values 
           are parent values. To specify values for only a subset of the 
           parents, only enter those parents in the dictionary. If only a 
           subset of parent values are specified, then the current values are 
           used for the remaining parents.
        :type parentinput: dict
        :arg valueinput: Optional. A legitimate value of the decision node 
           object. If no valueinput is specified, then the current value of the 
           node is used.
        :returns: the conditional probability of valueinput or the current
           value conditioned on parentinput or the current values of the 
           parents.
        
        .. note::
        
           If parent values are specified in parentinput, those values must 
           correspond to items in the space attributes of the parents.
           
        .. warning::
            
           The CPT is an np.zero array upon initialization. Therefore, one must 
           set the CPT wih :py:meth:`classes.DecisionNode.randomCPT()` or 
           manually before calling this method.
        
        """        
        if not self.CPT.any():
            raise RuntimeError('CPT for %s is just a zeros array' % self.name)
        if valueinput is None:
            valueinput = self.value
        valslist = self.dict2list_vals(parentinput, valueinput)
        indo = self.get_CPTindex(valslist)
        p = self.CPT[indo]
        return p  
        
    def logprob(self, parentinput={}, valueinput=None):
        """Compute the conditional logprob of the current or specified value
        
        :arg parentinput: Optional. Specify values of the parents at which to 
           compute the conditional logprob. Keys are parent names. Values are 
           parent values. To specify values for only a subset of the parents, 
           only enter those parents in the dictionary. If only a subset of 
           parent values are specified, then the current values are used for the 
           remaining parents.
        :type parentinput: dict
        :arg valueinput: Optional. A legitimate value of the decision node 
           object. If no valueinput is specified, then the current value of the 
           node is used.
        :returns: the conditional logprob of valueinput or the current
           value conditioned on parentinput or the current values of the 
           parents.
        
        .. note::
        
           If parent values are specified in parentinput, those values must 
           correspond to items in the space attributes of the parents.
           
        .. warning::
            
           The CPT is an np.zero array upon initialization. Therefore, one must 
           set the CPT wih :py:meth:`classes.DecisionNode.randomCPT()` or 
           manually before calling this method.
        
        """        
        r = self.prob(parentinput, valueinput)
        return np.log(r)
        
    def set_value(self, newvalue):
        """Set the current value of the DecisionNode object
        
        :arg newvalue: a legitimate value of the DecisionNode object, i.e. the 
           value must be in :py:attr:`classes.ChanceNode.space`.
        
        .. warning::
            
           When arbitrarily setting values, some children may have zero 
           probability given their parents. This means the logprob may be -inf. 
           If using, :py:meth:`seminfg.SemiNFG.loglike()`, this results in a 
           divide by zero error.
        
        """
        if type(newvalue==self.space[0]) is bool:
            if newvalue in self.space:
                self.value = newvalue
            else:
                errorstring = "the new value is not in "+self.name+"'s space"
                raise ValueError(errorstring)
        elif any((newvalue==y).all() for y in self.space):
            self.value = newvalue
        else:
            errorstring = "the new value is not in "+self.name+"'s space"
            raise ValueError(errorstring)  
        