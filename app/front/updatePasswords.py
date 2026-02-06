from models import *
import bcrypt

extendedPass = "H(&(ca.nRNYl#m"
extendedSalt = bcrypt.gensalt()
extendedPassB = bcrypt.hashpw(extendedPass.encode("utf8"), extendedSalt)
extendedUser = User.get(User.username=="ExtendedFamily")
extendedUser.password = extendedPassB
extendedUser.save()

familyPass = "&9Nnk/nw=kV<#w"
familySalt = bcrypt.gensalt()
familyPassB = bcrypt.hashpw(familyPass.encode("utf8"), familySalt)
familyUser = User.get(User.username=="Family")
familyUser.password = familyPassB
familyUser.save()
