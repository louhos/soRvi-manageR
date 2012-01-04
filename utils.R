# From Gavin Simpson @ StackOverfolw http://bit.ly/z4A5Wg

findfuns <- function(x) {
  if(require(x, character.only=TRUE)) {
    env <- paste("package", x, sep=":")
    nm <- ls(env, all=TRUE)
    nm[unlist(lapply(nm, function(n) exists(n, where=env,
                                            mode="function",
                                            inherits=FALSE)))]
  } else character(0)
}
pkgs <- c("sorvi")
z <-  lapply(pkgs, findfuns)
names(z) <- pkgs
Z <- sort(unique(unlist(z)))
