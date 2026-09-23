def valid_rpe(v):
 try:n=float(str(v).strip())
 except:return False
 return 1<=n<=10 and abs(n*2-round(n*2))<1e-6

def test_rpe_values():
 for v in (1,1.5,8,8.5,9.5,10):assert valid_rpe(v)
 for v in (0,0.5,8.3,10.5,85,-1,"x",""):assert not valid_rpe(v)

def test_target_ownership():
 target={"w":"47.5","r":"14"}; stale={"w":"60","r":"10","w_source":"target","r_source":"target"}
 for k in ("w","r"):
  if stale[k+"_source"]=="target":stale[k]=target[k]
 assert stale["w"]=="47.5" and stale["r"]=="14"
 user={"w":"50","r":"12","w_source":"user","r_source":"user"}
 for k in ("w","r"):
  if user[k+"_source"]=="target":user[k]=target[k]
 assert user=={"w":"50","r":"12","w_source":"user","r_source":"user"}