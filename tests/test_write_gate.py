import threading
import time
import unittest
from workflow.write_gate import Gate


class GateTests(unittest.TestCase):
    def test_waiting_writers_get_fifo_turns_before_reacquisition(self):
        gate=Gate();gate.acquire();order=[];threads=[]
        def run(i):
            gate.acquire()
            try:order.append(i)
            finally:gate.release()
        for i in range(4):
            t=threading.Thread(target=run,args=(i,));t.start();threads.append(t)
            deadline=time.monotonic()+5
            while True:
                with gate.condition:queued=len(gate.waiters)
                if queued==i+2:break
                self.assertLess(time.monotonic(),deadline);time.sleep(.001)
        gate.release()
        gate.acquire();order.append(4);gate.release()
        for t in threads:t.join(5);self.assertFalse(t.is_alive())
        self.assertEqual(order,[0,1,2,3,4])

    def test_nested_writer_rejected_without_losing_ownership(self):
        gate=Gate();gate.acquire()
        with self.assertRaises(RuntimeError):gate.acquire()
        gate.release();gate.acquire();gate.release()
