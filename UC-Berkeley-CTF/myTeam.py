# myTeam.py
# ---------
# Licensing Information:  You are free to use or extend these projects for
# educational purposes provided that (1) you do not distribute or publish
# solutions, (2) you retain this notice, and (3) you provide clear
# attribution to UC Berkeley, including a link to http://ai.berkeley.edu.
# 
# Attribution Information: The Pacman AI projects were developed at UC Berkeley.
# The core projects and autograders were primarily created by John DeNero
# (denero@cs.berkeley.edu) and Dan Klein (klein@cs.berkeley.edu).
# Student side autograding was added by Brad Miller, Nick Hay, and
# Pieter Abbeel (pabbeel@cs.berkeley.edu).


from captureAgents import CaptureAgent
import random, time, util
from game import Directions
import game
from util import nearestPoint

#################
# Team creation #
#################

def createTeam(firstIndex, secondIndex, isRed,
               first = 'SafeAgent', second = 'SafeAgent'):
  """
  This function should return a list of two agents that will form the
  team, initialized using firstIndex and secondIndex as their agent
  index numbers.  isRed is True if the red team is being created, and
  will be False if the blue team is being created.

  As a potentially helpful development aid, this function can take
  additional string-valued keyword arguments ("first" and "second" are
  such arguments in the case of this function), which will come from
  the --redOpts and --blueOpts command-line arguments to capture.py.
  For the nightly contest, however, your team will be created without
  any extra arguments, so you should make sure that the default
  behavior is what you want for the nightly contest.
  """

  # The following line is an example only; feel free to change it.
  return [eval(first)(firstIndex), eval(second)(secondIndex)]

##########
# Agents #
##########

# This is the original agent used for the Friendly Tournament
class SafeAgent(CaptureAgent):
  """
  This agent always plays it safe.
  """

  def defineBorder(self, gameState):
    layout = gameState.data.layout
    x = (layout.width / 2) - 1
    if self.red:    # red team is on the left side
      x -= 1
    borderCells = [(x, y) for y in range(0, layout.height) if not layout.isWall((x, y))]
    return borderCells

  def registerInitialState(self, gameState):
    CaptureAgent.registerInitialState(self, gameState)
    self.border = self.defineBorder(gameState)

  def chooseAction(self, gameState):
    actions = gameState.getLegalActions(self.index)

    values = [self.evaluate(gameState, a) for a in actions]
    
    maxValue = max(values)
    bestActions = [a for a,v in zip(actions, values) if v == maxValue]

    return random.choice(bestActions)

  def getSuccessor(self, gameState, action):
    """
    Finds the next successor which is a grid position (location tuple).
    """
    successor = gameState.generateSuccessor(self.index, action)
    pos = successor.getAgentState(self.index).getPosition()
    if pos != nearestPoint(pos):
      # Only half a grid position was covered
      return successor.generateSuccessor(self.index, action)
    else:
      return successor

  def evaluate(self, gameState, action):
    """
    Computes a linear combination of features and feature weights
    """
    features = self.getFeatures(gameState, action)
    weights = self.getWeights(gameState, action)
    return features * weights

  def getFeatures(self, gameState, action):
    """
    Returns a counter of features for the state
    """
    features = util.Counter()
    successor = self.getSuccessor(gameState, action)

    agentState = successor.getAgentState(self.index)
    team = [successor.getAgentState(i) for i in self.getTeam(successor)]
    enemies = [successor.getAgentState(i) for i in self.getOpponents(successor)]
    food = self.getFood(successor).asList()
    defendFood = self.getFoodYouAreDefending(successor).asList()
    defendCapsules = self.getCapsulesYouAreDefending(successor)

    # count the number of power capsules on our side that the enemy is closer to than we are
    features['unguardedCapsules'] = self.countUnguardedCapsules(team, enemies, defendCapsules)

    # count the number of food pellets that the enemy can capture successfully
    features['unguardedFood'] = self.countUnguardedFood(team, enemies, defendFood)

    if (not agentState.isPacman) and agentState.scaredTimer == 0:
      if agentState.getPosition() in [gameState.getAgentPosition(i) for i in self.getOpponents(gameState)]:
        features['eatsEnemy'] = 1
      else:
        features['closestEnemyDistance'] = self.getClosestEnemyDistance(agentState.getPosition(), enemies)
    elif self.getClosestEnemyDistance(agentState.getPosition(), enemies) < 2:
      features['certainDeath'] = 1
    elif agentState.isPacman and (not self.hasEscapeRoute(agentState.getPosition(), enemies)):
      features['certainDeath'] = 1

    # find the distance to the closest food on enemy side
    if len(food) >= len(self.getFood(gameState).asList()):
      features['closestFoodDistance'] = self.getClosestFoodDistance(agentState.getPosition(), food)
    else:
      features['eatsFood'] = 1

    if agentState.numCarrying > 0:
      features['closestBorder'] = min([self.getMazeDistance(agentState.getPosition(), b) for b in self.border])

    return features

  def getWeights(self, gameState, action):
    """
    Normally, weights do not depend on the gamestate.  They can be either
    a counter or a dictionary.
    """
    return {
      'unguardedFood': -10,
      'unguardedCapsules': -1000,
      'closestEnemyDistance': -10,
      'certainDeath': -5000,
      'closestFoodDistance': -1,
      'eatsFood': 100,
      'eatsEnemy': 200,
      'closestBorder': -1
    }

  def countUnguardedCapsules(self, team, enemies, defendCapsules):
    if len(defendCapsules) == 0:
      return 0
    teamPositions = [t.getPosition() for t in team]
    enemyPositions = [e.getPosition() for e in enemies]
    teamCapsDist = [min(self.getMazeDistance(i, teamPositions[0]), self.getMazeDistance(i, teamPositions[1])) for i in defendCapsules]
    enemyCapsDist = [min(self.getMazeDistance(i, enemyPositions[0]), self.getMazeDistance(i, enemyPositions[1])) for i in defendCapsules]
    # to guard a power capsule, we must be 2 steps closer to it than the enemy
    return len([t for t,e in zip(teamCapsDist, enemyCapsDist) if t >= e + 1])

  def countUnguardedFood(self, team, enemies, defendFood):
    count = 0
    for enemy in enemies:
      if enemy.numCarrying > 0:
        enemyClosestBorder = min([(b, self.getMazeDistance(enemy.getPosition(), b)) for b in self.border], key=lambda x: x[1])
        teamBorderDist = min(self.getMazeDistance(team[0].getPosition(), enemyClosestBorder[0]), self.getMazeDistance(team[1].getPosition(), enemyClosestBorder[0]))
        if enemyClosestBorder[1] <= teamBorderDist:
          count += enemy.numCarrying
      else:
        if len(defendFood) > 0:
          enemyClosestSteal = min([(f, self.getMazeDistance(f, enemy.getPosition()) + min([self.getMazeDistance(f, b) for b in self.border])) for f in defendFood], key=lambda x: x[1])
          enemyClosestBorder = min([(b, self.getMazeDistance(enemyClosestSteal[0], b)) for b in self.border], key=lambda x: x[1])
          teamBorderDist = min(self.getMazeDistance(team[0].getPosition(), enemyClosestBorder[0]), self.getMazeDistance(team[1].getPosition(), enemyClosestBorder[0]))
          if enemyClosestBorder[1] <= teamBorderDist:
            count += 1
    return count
  
  def getClosestFoodDistance(self, position, food):
    if len(food) > 0:
      return min([(self.getMazeDistance(position, f)) for f in food])
    else:
      return 0

  def getClosestEnemyDistance(self, position, enemies):
    return min([self.getMazeDistance(position, e.getPosition()) for e in enemies])

  def hasEscapeRoute(self, position, enemies):
    flag = False
    borderDist = [self.getMazeDistance(position, b) for b in self.border]
    enemyBorderDist = [min(self.getMazeDistance(b, enemies[0].getPosition()), self.getMazeDistance(b, enemies[1].getPosition())) for b in self.border]
    for (d, e) in zip(borderDist, enemyBorderDist):
      if d < e:
        flag = True
    return flag

# This is an experiment (work in progress...)
class OptimizingAgent(CaptureAgent):
  """
  This agent tries to maximize its team's score
  """

  def defineBorder(self, gameState):
    layout = gameState.data.layout
    x = (layout.width / 2) - 1
    # red border on left, blue border on right
    blueBorder = [(x, y) for y in range(0, layout.height) if not layout.isWall((x, y))]
    x -= 1
    redBorder = [(x, y) for y in range(0, layout.height) if not layout.isWall((x, y))]
    if self.red:
      self.border = redBorder
      self.enemyBorder = blueBorder
    else:
      self.border = blueBorder
      self.enemyBorder = redBorder

  def registerInitialState(self, gameState):
    CaptureAgent.registerInitialState(self, gameState)
    self.defineBorder(gameState)

  def chooseAction(self, gameState):
    actions = gameState.getLegalActions(self.index)

    values = [self.evaluate(gameState, a) for a in actions]
    
    maxValue = max(values)
    bestActions = [a for a,v in zip(actions, values) if v == maxValue]

    return random.choice(bestActions)

  def getSuccessor(self, gameState, action):
    """
    Finds the next successor which is a grid position (location tuple).
    """
    successor = gameState.generateSuccessor(self.index, action)
    pos = successor.getAgentState(self.index).getPosition()
    if pos != nearestPoint(pos):
      # Only half a grid position was covered
      return successor.generateSuccessor(self.index, action)
    else:
      return successor

  def evaluate(self, gameState, action):
    successor = self.getSuccessor(gameState, action)

    # agentState = successor.getAgentState(self.index)
    team = [successor.getAgentState(i) for i in self.getTeam(successor)]
    enemies = [successor.getAgentState(i) for i in self.getOpponents(successor)]
    food = self.getFood(successor).asList()
    defendFood = self.getFoodYouAreDefending(successor).asList()
    # defendCapsules = self.getCapsulesYouAreDefending(successor)
    # number of moves current agent has left
    # remainingMoves = successor.data.timeleft // 4

    score = self.getScore(successor)
    predictedGains = self.countUnguardedFood(team, enemies, food)
    predictedLosses = self.countUnguardedDefendFood(team, enemies, defendFood)

    # distToBorder = 0
    # if predictedGains == predictedLosses:
    #   distToBorder = min([self.getMazeDistance(successor.getAgentPosition(self.index), b) for b in self.border])
    # print('Agent: {}, Action {}'.format(self.index, action))
    # print('Score: {}'.format(score))
    # print('Gains: {}'.format(predictedGains))
    # print('Losses: {}'.format(predictedLosses))


    return score + predictedGains - predictedLosses

  def getClosestPositionAndDistance(self, position, positionList):
    return min([(p, self.getMazeDistance(position, p)) for p in positionList], key=lambda x: x[1])

  def countUnguardedFood(self, team, enemies, food):
    unguardedFood = 0
    # all foods that we can safely steal
    for f in food:
      (border, distance) = self.getClosestPositionAndDistance(f, self.border)
      distance += min([self.getMazeDistance(t.getPosition(), f) for t in team])
      if self.getClosestPositionAndDistance(border, [e.getPosition() for e in enemies])[1] > (distance + 1):
        unguardedFood += 1
    for t in team:
      (border, distance) = self.getClosestPositionAndDistance(t.getPosition(), self.border)
      if self.getClosestPositionAndDistance(border, [e.getPosition() for e in enemies])[1] > (distance + 1):
        unguardedFood += t.numCarrying
    return unguardedFood

  def countUnguardedDefendFood(self, team, enemies, defendFood):
    unguardedFood = 0
    # all foods that enemy can safely steal w/out relying on ghosts being scared (assuming they have enough time)
    for f in defendFood:
      (border, distance) = self.getClosestPositionAndDistance(f, self.enemyBorder)
      distance += min([self.getMazeDistance(e.getPosition(), f) for e in enemies])
      if self.getClosestPositionAndDistance(border, [t.getPosition() for t in team])[1] > (distance + 1):
        unguardedFood += 1
    for e in enemies:
      (border, distance) = self.getClosestPositionAndDistance(e.getPosition(), self.enemyBorder)
      if self.getClosestPositionAndDistance(border, [t.getPosition() for t in team])[1] > (distance + 1):
        unguardedFood += e.numCarrying
    return unguardedFood


# class DummyAgent(CaptureAgent):
#   """
#   A Dummy agent to serve as an example of the necessary agent structure.
#   You should look at baselineTeam.py for more details about how to
#   create an agent as this is the bare minimum.
#   """

#   def registerInitialState(self, gameState):
#     """
#     This method handles the initial setup of the
#     agent to populate useful fields (such as what team
#     we're on).

#     A distanceCalculator instance caches the maze distances
#     between each pair of positions, so your agents can use:
#     self.distancer.getDistance(p1, p2)

#     IMPORTANT: This method may run for at most 15 seconds.
#     """

#     '''
#     Make sure you do not delete the following line. If you would like to
#     use Manhattan distances instead of maze distances in order to save
#     on initialization time, please take a look at
#     CaptureAgent.registerInitialState in captureAgents.py.
#     '''
#     CaptureAgent.registerInitialState(self, gameState)

#     '''
#     Your initialization code goes here, if you need any.
#     '''


#   def chooseAction(self, gameState):
#     """
#     Picks among actions randomly.
#     """
#     actions = gameState.getLegalActions(self.index)

#     '''
#     You should change this in your own agent.
#     '''

#     return random.choice(actions)

