def SieveOfEratosthenes(num):
    prime = [True for i in range(num+1)]
    # boolean array
    p = 2
    while (p * p <= num):
 
        # If prime[p] is not
        # changed, then it is a prime
        if (prime[p] == True):
 
            # Updating all multiples of p
            for i in range(p * p, num+1, p):
                prime[i] = False
        p += 1
 
    primes = []
    for p in range(2, num+1):
        if prime[p]:
            primes.append(p)
    return primes