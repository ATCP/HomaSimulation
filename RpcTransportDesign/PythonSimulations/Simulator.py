#!/usr/bin/python

# Copyright (c) 2015 Stanford University
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR(S) DISCLAIM ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL AUTHORS BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""
Runs a simplified simulations for the credit based transport scheme.
"""
import os
import sys
import random
import numpy as np
from optparse import OptionParser

"""
"""

## @var avgDelay: The mean value for the delay distribution function. This value
# is an integer.
avgDelay = 3

## @var fixedDelay: The constant delay every packet will experience in the
#  network. This parameter is an integer.
fixedDelay = 1

def generateMsgSize(distMatrix):
    """A helper function that generates a message size from the cumulative
    probability distribution that is given as the input argument to this
    function.

    @param  distMatrix: @see run()
    @type   distMatrix: @see run()

    @return: A message size value generated from the input probability
             distribution.
    @rtype:  An integer.
    """
    randomNumber = random.random()
    for row in distMatrix:
        if (row[0] > randomNumber):
            return row[1]


class Scheduler():
    """This class creates the common internal context for an arbitrary scheduler
    and implements the interface to various schedulers. If a new scheduler is to
    be added, this class is the right place to implement that scheduler as a
    function of it.

    ===Definition of internal variables===
    @var    msg: A message that will be generated at sender and must be
                 transmitted. A list of [message_id, message_size]. Both values
                 in this list are integers.

    @var    delayedPkt: Represent a packet that is taken out of txQueue and
                        should be received in rxQueue after some delay value. A
                        list of [pkt[:], delay]. For type of pkt, please see
                        @see Scheduler::addPktToDelayQueue
                        delay is an integer.
    """

    def __init__(self, txQueue = [], rxQueue = [], delayQueue = []):
        """
        @param  txQueue: The transmit queue at the input of simulation. A list
                         of messages as [msg1, msg2, ..] that are sorted by the
                         message size from smallest to largest. Every time a new
                         messge is generated for this simulation, it will be
                         added to this queue. Messgaes are of type @see msg.
        @type   txQueue: C[msg, msg, msg, ...]

        @param  rxQueue: Reperesent a list of pkt that are scheduled and
                         received in the output (edge) queue of the network.
                         This practically is a list of packets as [pkt1, pkt2,
                         ...] that are sorted by the priority from highest
                         priority (smallest value) to lowest priority.
        @type   rxQueue: C[pkt, pkt, pkt, ..]

        @param  delayQueue: This queue contains all packets that are scheduled
                            and has left txQueue but has not yet received in
                            rxQueue.  This queue essentially models the network
                            so packets in this queue are in flight and
                            experiencing some delay in the network. This is a
                            list of [delayedPkt1, delayedPkt2, ...] and this
                            list is sorted by the delay of the packets from
                            lowest to highest. delayedPkts are of type @see
                            delayedPkt .
        @type   delayQueue: C[delayedPkt, delayedPkt, ...]
        """
        self.txQueue = txQueue
        self.rxQueue = rxQueue
        self.delayQueue= delayQueue 

    def addPktToDelayQueue(self, pkt, avgDelay):
        """This function models the network in a very simple way by only taking
        the network delay into account. For every packet that is to transmitted
        over, this model assumes that the network has full bisection bandwidth
        and it only add some random delay to the transmision time of the packet.
        Every time a packet enters this model, it will be added to a the \p
        delayQueue and will leave the this queue after some random delay. The
        delay model is assumed to be some fixed delay \p avgDelay plus some
        random delay from a Poisson distribution with mean avgDelay.

        @param  pkt: A list of [message_id, message_size, priority]. Represents
                     a packet from a message along with the granted priority for
                     that packet and the remaining size of message that this
                     packet blongs to.
        @type   pkt: list[int, int, int]

        @param  avgDelay: See @see avgDelay
        """
        msgId = pkt[0]
        msgSize = pkt[1]
        pktPrio = pkt[2]

        # Sample delay from a Poisson distribution. Then create a \p delayedPkt
        # and and add it to the \p dealyQueue.
        delay = np.random.poisson(avgDelay) + fixedDelay
        delayedPkt = list([msgId, msgSize, pktPrio, delay])
        self.delayQueue.append(delayedPkt)
        self.delayQueue.sort(cmp=lambda x, y: cmp(x[3], y[3]))

    def depleteDelayQueue(self):
        """This function practically abstracts out the propagation of the packets
        out of the network and to the @p rxQueue. Everytime a packet is
        completely transmitted through the network, it will add that packet to
        the @p rxQueue and makes sure the rxQueue is kept sorted with respect to
        packet priorities.
        """
        for delayedPkt in self.delayQueue[:]:
            if (delayedPkt[-1] == 0):
                pkt = delayedPkt[0:-1] 
                self.rxQueue.append(pkt)
                self.delayQueue.remove(delayedPkt)
        self.rxQueue.sort(cmp=lambda x, y: cmp(x[2], y[2]))

        for delayedPkt in self.delayQueue:
            delayedPkt[-1] -= 1

    def simpleScheduler(self, slot, pktOutTimes):
        """Impements the most simple SRPT scheduler scheme. At any simulation round,
        if there are messages pending for transmission, this module tries to
        minimize the latency for the shortest messages (SRPT - shortest remaining
        time first - scheduling) so it takes a packet from the message with the
        smallest size and propagates it throught the network by appying the
        simple network model we have implemented in this class.  Subsequently at
        every round, between all the packets that has completely traveresed the
        network, this module takes a packet in FIFO mode and puts it out of the
        simulation.

        ===Additional info===
        This scheduler can only schedule one packet in every scheduling round
        (one round = one packet time). If delay was deterministic, this one
        packet per round would be enough to achieve our goal that is minimizing
        the latency of small messages. But stochastic delay could cause bubbles
        in rxQueue output port and prevent us from achieving our goal: For
        example let's consider this scenario: msg1 and msg2 both have size 1. In
        the first round the scheduler chooses packet from msg1 and in the round
        2 msg2 will be scheduled. But assume that packet from msg1 will
        exprience a large delay  and packet from msg2 that packet will
        experience the minimum delay. So if the scheduler knew in advance that
        the second pkt would experience less delay, it would have scheduled it
        in the first round and that message would have completed earlier.

        @param  slot: The simulation round for which this scheduler is run.
        @type   slot: An integer.

        @retun  pktOutTimes: @see run() 
        @rtype  pktOutTimes: @see run()
        """
        prio = 0 # The priority of all packets are the same
        if (len(self.txQueue) > 0):

            # Take the highest priority packet from the txQueueu and propaget it
            # through the network by adding it to the delayQueue.
            highPrioMsg = self.txQueue[0]
            highPrioPkt = list([highPrioMsg[0], highPrioMsg[1], prio])
            highPrioMsg[1] -= 1
            self.addPktToDelayQueue(highPrioPkt, avgDelay)    
            if (highPrioMsg[1] == 0):
                self.txQueue.pop(0)
                
        # For the packets that have completely taransmitted through the network,
        # put them in the rxQueue. Subsequently remove a packet from head of the
        # line in the rxQueue and record its packet info in the @p pktOutTimes.
        self.depleteDelayQueue()
        if (len(self.rxQueue) > 0):
            pkt = self.rxQueue.pop(0)
            msgId = pkt[0]
            msgSize = pkt[1]
            pktPrio = pkt[2]
            if (msgId in pktOutTimes):
                pktOutTimes[msgId].append([slot, pktPrio, msgSize])
            else:
                pktOutTimes[msgId] = list()
                pktOutTimes[msgId].append([slot, pktPrio, msgSize])

    def idealScheduler(self, slot, pktOutTimes):
        """Implements the ideal scheduler (Oracle scheduler).
        Because the network delay is a random variable, the simple scheduler
        might not lead to the best latency. For example, a packet from a smaller
        message might experience higher latency than a packet from a larger
        message that is scheduled in the next round therefore the packet from
        the larger message will be received earlier in the rxQueue. Since the
        rxQueue is FIFO for simple scheduler the packet from the larger message
        will cause HOL for the packet from the smaller message and therefore the
        simple scheduler will not achieve its goal that is minimizing the
        latency of the smallest message. The ideal scheduler instead have many
        priorities in the rxQueue (one priority per message size) therefore no
        HOL can happen in rxQueue. 
        On the other hand, in order to compensate for the effect of random delay
        on the messages of same size or messages that are slightly different in
        size, the ideal scheduler will schedule more than one packet in each
        round. In principle if we know how much delay each packet will
        exprience, we might sometimes want to prioritize packets from slightly
        larger messages over packets from smaller message if we knew packets
        from smaller message will experience much higher delay. The ideal
        scheduler in fact overcome this problem by scheduling one packet from
        every message in the txQueue at each round and allows all messages to
        transmit one packet (rather than scheduling one packet only from the
        smallest message as simple scheduler does). Then as the packets are
        received in rxQueue, they will be prioritized based on the remaining
        message size. The scheduler then take the highest priority packet
        (packet from the message with smallest remaining size) and removes it
        from the queue.
        This scheduler completely hides the effect of random variation in delay
        and because of infinite priorities no HOL can happen in this ideal
        scheme. This scheme is the best we can do for the scheduler.
        
        @param  slot: The simulation round for which this scheduler is run.
        @type   slot: An integer.

        @retun  pktOutTimes: @see run() 
        @rtype  pktOutTimes: @see run()

        """
        for msg in self.txQueue[:]:

            # Set the priority same as the size
            pkt = list([msg[0], msg[1], msg[1]])
            self.addPktToDelayQueue(pkt, avgDelay)
            if (msg[1] == 1):
                self.txQueue.remove(msg)
            else:
                msg[1] -= 1
            
        self.depleteDelayQueue() 
        if (len(self.rxQueue) > 0):
            pkt = self.rxQueue.pop(0)
            msgId = pkt[0]
            msgSize = pkt[1]
            pktPrio = pkt[2]
            if (msgId in pktOutTimes):
                pktOutTimes[msgId].append([slot, pktPrio, msgSize])
            else:
                pktOutTimes[msgId] = list()
                pktOutTimes[msgId].append([slot, pktPrio, msgSize])  

def run(steps, rho, distMatrix, msgDict, pktOutTimes):
    """Starts the simulations for different schedulers and returns packet level
    inofrmation after simulation is over. This function works like a wrapper
    around the simulation scenario so it is the right place to add new
    simulation experiments. 
    
    @param  steps: Number of rounds for which the simulation will run.
    @type   steps: An integer.

    @param  rho: Defines the average input rate at which packets will be
                 generated in this simulation. 
    @type   rho: A float number between 0 and 1.

    @param  distMatrix: A list (matrix) that defined the cumulative probability
                        distribution of message sizes. From the lowest size to
                        the highest size, for each size there is a row in this
                        matrix as row=[cumulative_probability, size]. So this
                        matrix is formed as a list of [row1, row2, ...]
    @type   distMatrix: list[[float, int], [float, int], ...]


    @return msgDict: A dict of all messages that will be generated in this
                     simulation. Each message in this dictionary will be
                     identified by a unique that is the message_id mapped to a
                     value that is a list of  message size and the time slots 
                     at which that message is genereated.
                     So the msgDict is a dict{key(messageId):value([messageSize,
                     time_slot)]
    @rtype  msgDict: dict{key(int) : value(list[int, int])}

    @return pktOutTimes: Record the out timeslot for every individual packet
                         within for each message for each scheduler type. This
                         is a dictionary from key:scheduler_type to a
                         value:dict().  Each value itself is a dictionary from
                         key:message_id to a value:list[pkt_info]. Each pkt_info
                         in this list is some information for one packet that
                         belongs to that message identified by message_id. Each
                         pkt_info is a list of three elements as
                         pkt_info[time_slot, priority, msgSize] that is the time
                         slot at which the packet has left the rxQueue
                         (completed the simulation cycle) and the priority that
                         was assigned to that packet by the scheduler and the
                         remaining size of the message when that packet was
                         scheduled. 
    @rtype  pktOutTimes: dict{ key(scheduler) :
                               value( dict{ key(messge_id) : 
                                            value([pkt_info1, pkt_info2,..]) } }

    """
    sizeAvg = 0
    prevProb = 0

    # Find the average size of messages from the distribution list.
    for row in distMatrix: 
        sizeAvg += row[1] * (row[0] - prevProb)
        prevProb = row[0]

    probPerSlot = rho / sizeAvg # The prbability by which new messages will be
                                # added to the txQueue.
    txQueue = list()
    rxQueue = list() 
    delayQueue = list()
    scheduler = Scheduler(txQueue, rxQueue, delayQueue)
    msgId = 0

    # Generate a new message in each step for \p steps and run the simple
    # scheduler until all packets entered simulations have eventually left the
    # simulation. Then it return the result in \p pktOutTimes.
    for slot in range(steps):
        if (random.random() < probPerSlot):
            newMsg = [msgId, generateMsgSize(distMatrix)]
            txQueue.append(newMsg[:]) 
            txQueue.sort(cmp=lambda x, y: cmp(x[1], y[1]))
            msgDict[msgId] = [newMsg[1], slot] 
            msgId += 1

        scheduler.simpleScheduler(slot, pktOutTimes['simple'])

    while len(txQueue) or len(rxQueue) or len(delayQueue):
        slot += 1
        scheduler.simpleScheduler(slot, pktOutTimes['simple'])

    # Run ideal scheduler for the exact same message distribution as the one we
    # ran simple scheduler for in previous loop.
    txQueue = list()
    rxQueue = list() 
    delayQueue = list()
    scheduler = Scheduler(txQueue, rxQueue, delayQueue)
    msgId = 0
    for slot in range(steps):
        if (msgId in msgDict and msgDict[msgId][1] == slot):
            newMsg = [msgId, msgDict[msgId][0]]
            txQueue.append(newMsg[:]) 
            txQueue.sort(cmp=lambda x, y: cmp(x[1], y[1]))
            msgId += 1
        scheduler.idealScheduler(slot, pktOutTimes['ideal'])   
    
    while len(txQueue) or len(rxQueue) or len(delayQueue):
        slot += 1
        scheduler.idealScheduler(slot, pktOutTimes['ideal'])

if __name__ == '__main__':
    parser = OptionParser(description='Runs a simplified simulations for'
            ' credit based transport schemes.')
    parser.adding('--inputDir', metavar='DIR', default='input', dest='inputDir',
            help='Directory containing input files for this simulation.')
    parser.adding('--outputDir', metavar='DIR', default='output',
            dest='outputDir',
            help='Target directory that will coantain output files after'
            ' simulation.')
    parser.add_option('--slots', type=int, metavar='N', default=10000,
            dest='steps',
            help='Total number of steps that this simulation should run.')
    parser.add_option('--inputRate', type=float, metavar='RATE', default=0.5,
            dest='rho',
            help='Average Ratio input packet rate to output packet rate')
    parser.add_option('--sizeDist', metavar='FILE_NAME',
            default='SizeDistribution', dest='distFileName',
            help='Name of the input file containing the cumulative distribution'
            ' of message sizes.')
    (options, args) = parser.parse_args()
    inputDir = options.inputDir
    outputDir = options.outputDir
    steps = options.steps
    rho = options.rho
    distFileName = options.distFileName

    distMatrix = []
    f = open(inputDir + '/' + distFileName, 'r')
    for line in f:
        if (line[0] != '#' and line[0] != '\n'):
            distMatrix.append(map(float, line.split( )))
    f.close()

                                                           

    pktOutTimes = dict()
    msgDict = dict()

    #run(steps, rho, sizeAvg, distMatrix, msgDict, pktOutTimes)
    #pktOutTimesSimple= pktOutTimesSimple['simple']
    #for key in msgDict:
    #    print "msgId: {}, msgSize: {}, beginTime: {}, pkts: {}".format(key, 
    #            msgDict[key][0], msgDict[key][1],
    #            pktOutTimesSimple[key] if key in pktOutTimesSimple else [])

    f = open(outputDir + '/' + 'ideal_vs_simple_penalty', 'w')
    f.write("\tpenalty\trho\tavg_delay\n")
    fd = open(outputDir + '/' + 'ideal_vs_simple_rho_fixed', 'w')
    fd.write("\tpenalty\tsize\trho\n")

    # Change rho, and calculate penalty of simple scheduler vs ideal
    # scheduler.
    for n, rho in enumerate([x/100.0 for x in range(15, 105, 10)]):
        pktOutTimes = dict() 
        pktOutTimes['simple'] = dict()
        pktOutTimes['ideal'] = dict()
        msgDict = dict()
        run(steps, rho, distMatrix, msgDict, pktOutTimes)
        penalty = 0.0
        pktOutTimesSimple = pktOutTimes['simple']
        pktOutTimesIdeal = pktOutTimes['ideal']
        numMsg = 0

        # type of penaltyPerSize: 
        # Dict{ key(msgSize): value([totalPenalty, msgCount, rho]) }
        penaltyPerSize = dict()  
        for key in pktOutTimesSimple:
            if key in pktOutTimesIdeal:
                pktTimesSimple = [pkt_inf[0] for pkt_inf in
                    pktOutTimesSimple[key]]
                msgCompletionTimeSimple = max(pktTimesSimple) - msgDict[key][1]
                pktTimesIdeal = [pkt_inf[0] for pkt_inf in
                    pktOutTimesIdeal[key]]
                msgCompletionTimeIdeal = max(pktTimesIdeal) - msgDict[key][1]
                
                numMsg += 1 
                
                # Total penalty
                penalty += ((msgCompletionTimeSimple -
                        msgCompletionTimeIdeal) * 1.0 / msgCompletionTimeIdeal)
                

                # Record penalty imposed on the current msgSize
                msgSize = msgDict[key][0]
                if (msgSize in penaltyPerSize):
                    penaltyPerSize[msgSize][0] += ((msgCompletionTimeSimple -
                        msgCompletionTimeIdeal) * 1.0 / msgCompletionTimeIdeal)
                    penaltyPerSize[msgSize][1] += 1
                else:
                    penaltyPerSize[msgSize] = [0.0, 0, rho]
                    penaltyPerSize[msgSize][0] += ((msgCompletionTimeSimple -
                        msgCompletionTimeIdeal) * 1.0 / msgCompletionTimeIdeal)
                    penaltyPerSize[msgSize][1] += 1

        f.write("{}\t{}\t{}\t{}\n".format(n+1, penalty/numMsg,
                rho, avgDelay+fixedDelay))

        for key in penaltyPerSize:
            fd.write("{}\t{}\t{}\n".format(
                    penaltyPerSize[key][0]/penaltyPerSize[key][1] if
                    penaltyPerSize[key][1] != 0 else 0.0, key, rho))
        
    fd.close() 
    f.close()
