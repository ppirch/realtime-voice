import argparse
import time

def main():
    p=argparse.ArgumentParser(); p.add_argument('--audio',required=True); a=p.parse_args()
    t=time.perf_counter(); print({'audio':a.audio,'wall_seconds':time.perf_counter()-t,'status':'backend-not-configured'})
if __name__=='__main__': main()
