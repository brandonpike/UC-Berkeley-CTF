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

class SafeAgent(CaptureAgent):
  """
  This agent always plays it safe.
  """

  def defineBorder(self, gameState):
    layout = gameState.data.layout
    x = (layout.width / 2) - 1
    # red on left, blue on right
    redBorder = [(x - 1, y) for y in range(0, layout.height) if not layout.isWall((x - 1, y))]
    # redThreshold = [(x - 1, y) for y in range(0, layout.height) if not layout.isWall((x, y))]
    blueBorder = [(x, y) for y in range(0, layout.height) if not layout.isWall((x, y))]
    # blueThreshold = [(x, y) for y in range(0, layout.height) if not layout.isWall((x - 1, y))]

    if self.red:
      self.border, self.enemyBorder = redBorder, blueBorder
    else:
      self.border, self.enemyBorder = blueBorder, redBorder


  def registerInitialState(self, gameState):
    """
    This method handles the initial setup of the
    agent to populate useful fields (such as what team
    we're on).

    A distanceCalculator instance caches the maze distances
    between each pair of positions, so your agents can use:
    self.distancer.getDistance(p1, p2)

    IMPORTANT: This method may run for at most 15 seconds.
    """

    '''
    Make sure you do not delete the following line. If you would like to
    use Manhattan distances instead of maze distances in order to save
    on initialization time, please take a look at
    CaptureAgent.registerInitialState in captureAgents.py.
    '''
    CaptureAgent.registerInitialState(self, gameState)

    '''
    Your initialization code goes here, if you need any.
    '''
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
    features['unguardedFood'] = self.countUnguardedFood(enemies, team, self.border, defendFood)

    # count the number of food pellets that we can capture successfully
    features['capturableFood'] = self.countCapturableFood(team, enemies, self.border, food)

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
      'unguardedFood': -20,
      'capturableFood': 10,
      'unguardedCapsules': -200,
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
    return len([t for t,e in zip(teamCapsDist, enemyCapsDist) if e <= t + 1])

  def countCapturableFood(self, attackers, defenders, attackerBorder, food):
    count = 0
    # count all foods we can safely steal
    for f in food:
      # borderDistance = min([self.getMazeDistance(b, f) for b in attackerBorder])
      borderTarget, borderDistance = self.getClosestPositionAndDistance(f, attackerBorder)
      attackerDistance = min([self.getMazeDistance(a.getPosition(), f) for a in attackers])
      defenderDistance = min([self.getMazeDistance(d.getPosition(), borderTarget) for d in defenders])
      if (borderDistance + attackerDistance + 1) < (defenderDistance):
        count += 1
    for a in attackers:
      (exitPosition, exitDistance) = self.getClosestPositionAndDistance(a.getPosition(), attackerBorder)
      interceptionDistance = min([self.getMazeDistance(d.getPosition(), exitPosition) for d in defenders])
      if (exitDistance + 1) < interceptionDistance:
        count += a.numCarrying
    return count

  def countUnguardedFood(self, attackers, defenders, defenderBorder, defendFood):
    count = 0
    # count all foods that can be safely captured by opponent
    for f in defendFood:
      # borderDistance = min([self.getMazeDistance(b, f) for b in defenderBorder])
      borderTarget, borderDistance = self.getClosestPositionAndDistance(f, defenderBorder)
      attackerDistance = min([self.getMazeDistance(a.getPosition(), f) for a in attackers])
      defenderDistance = min([self.getMazeDistance(d.getPosition(), borderTarget) for d in defenders])
      if (borderDistance + attackerDistance) < (defenderDistance + 2):
        count += 1
    for a in attackers:
      (exitPosition, exitDistance) = self.getClosestPositionAndDistance(a.getPosition(), defenderBorder)
      interceptionDistance = min([self.getMazeDistance(d.getPosition(), exitPosition) for d in defenders])
      if exitDistance < interceptionDistance:
        count += a.numCarrying
    return count

  def getClosestPositionAndDistance(self, position, positionList):
    return min([(p, self.getMazeDistance(position, p)) for p in positionList], key=lambda x: x[1])
    
  def getClosestFoodDistance(self, position, food):
    if len(food) > 0:
      return min([(self.getMazeDistance(position, f)) for f in food])
    else:
      return 0

  def getClosestEnemyDistance(self, position, enemies):
    return min([self.getMazeDistance(position, e.getPosition()) for e in enemies])

  def hasEscapeRoute(self, position, enemies):
    (exitPosition, exitDistance) = self.getClosestPositionAndDistance(position, self.border)
    interceptionDistance = min([self.getMazeDistance(e.getPosition(), exitPosition) for e in enemies])
    if (exitDistance + 1) < interceptionDistance:
      return True
    else:
      return False