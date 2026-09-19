# Query Output

## 1. SELECT/WHERE — in-stock books priced under £20

```
                                            title  price_gbp  in_stock
                             In a Dark, Dark Wood      19.63         1
                                 A Murder in Time      16.64         1
           That Darkness (Gardiner and Renner #1)      13.92         1
             Tastes Like Fear (DI Marnie Rome #3)      10.69         1
          A Study in Scarlet (Sherlock Holmes #1)      16.73         1
                       Hide Away (Eve Duncan #20)      11.84         1
                                Playing with Fire      13.71         1
        The Cuckoo's Calling (Cormoran Strike #1)      19.21         1
                                The Girl You Lost      12.29         1
        The Girl In The Ice (DCI Erika Foster #1)      15.85         1
                                      Lilac Girls      17.28         1
       The Constant Princess (The Tudor Court #1)      16.62         1
A Spy's Devotion (The Regency Spies of London #1)      16.97         1
```

## 2. ORDER BY + LIMIT — 5 most expensive books

```
                                                                 title  price_gbp
                                         Boar Island (Anna Pigeon #19)      59.48
The No. 1 Ladies' Detective Agency (No. 1 Ladies' Detective Agency #1)      57.70
                                      A Year in Provence (Provence #1)      56.88
                                                   The Past Never Ends      56.50
                                      The Last Painting of Sara de Vos      55.55
```

## 3. DISTINCT — distinct rating values present

```
 rating
      1
      2
      3
      4
      5
```

## 4. BETWEEN — books priced between £20 and £40

```
                                                                                            title  price_gbp
                                                             Blood Defense (Samantha Brinkman #1)      20.30
                                                                             Love, Lies and Spies      20.55
                                                                           Between Shades of Gray      20.79
                                                 Delivering the Truth (Quaker Midwife Mystery #1)      20.89
                                                                           Voyager (Outlander #3)      21.07
                                                                The Silkworm (Cormoran Strike #2)      23.05
The Road to Little Dribbling: Adventures of an American in Britain (Notes From a Small Island #2)      23.21
                                                              Career of Evil (Cormoran Strike #3)      24.72
                                              The Mysterious Affair at Styles (Hercule Poirot #1)      24.80
                                What Happened on Beale Street (Secrets of the South Mysteries #2)      25.37
                                                               Extreme Prey (Lucas Davenport #26)      25.40
                                                                                         Starlark      25.83
                                                               1,000 Places to See Before You Die      26.08
                                                                        Girl With a Pearl Earring      26.77
                                                                 Poisonous (Max Revere Novels #3)      26.80
                                                                                        The Widow      27.26
                                                                            Lost Among the Living      27.70
                                                                        The Marriage of Opposites      28.08
                                                                            The Passion of Dolssa      28.32
                        Forever and Forever: The Courtship of Henry Longfellow and Fanny Appleton      29.69
                                                                                     Mrs. Houdini      30.25
                                                                         The Great Railway Bazaar      30.54
                                                  World Without End (The Pillars of the Earth #2)      32.97
                                                                                The Secret Healer      34.56
                                                                                      Most Wanted      35.28
                                                                                     The Red Tent      35.66
                              Vagabonding: An Uncommon Guide to the Art of Long-Term World Travel      36.94
                                                                            The House by the Lake      36.95
                                                                             Under the Tuscan Sun      37.33
                                                                           The Invention of Wings      37.34
                                                            In the Woods (Dublin Murder Squad #1)      38.38
                                                        Neither Here nor There: Travels in Europe      38.95
                                                                                A Paris Apartment      39.01
```

## 5. IN — books rated 4 or 5 stars

```
                                                                   title  rating
                                      1,000 Places to See Before You Die       5
                                  A Time of Torment (Charlie Parker #14)       5
       What Happened on Beale Street (Secrets of the South Mysteries #2)       5
The Bachelor Girl's Guide to Murder (Herringford and Watts Mysteries #1)       5
                                       The Silkworm (Cormoran Strike #2)       5
                                                       The Girl You Lost       5
                                 A Flight of Arrows (The Pathfinders #2)       5
                                                            Mrs. Houdini       5
                                                   The Passion of Dolssa       5
                                                  Voyager (Outlander #3)       5
                                                            The Red Tent       5
                                                  Between Shades of Gray       5
                                                     While You Were Mine       5
                       A Spy's Devotion (The Regency Spies of London #1)       5
        Full Moon over Noah’s Ark: An Odyssey to Mount Ararat and Beyond       4
                                        A Year in Provence (Provence #1)       4
                                                           Sharp Objects       4
                                                     The Past Never Ends       4
                         The Murder of Roger Ackroyd (Hercule Poirot #4)       4
                   Murder at the 42nd Street Library (Raymond Ambler #1)       4
                        Delivering the Truth (Quaker Midwife Mystery #1)       4
                     The Mysterious Affair at Styles (Hercule Poirot #1)       4
  The No. 1 Ladies' Detective Agency (No. 1 Ladies' Detective Agency #1)       4
                                               The Marriage of Opposites       4
                                                       A Paris Apartment       4
                         World Without End (The Pillars of the Earth #2)       4
                                                   Lost Among the Living       4
```

## 6. JOIN — top 3 highest-rated books per category

```
     category_name                                                                    title  rating
Historical Fiction                                  A Flight of Arrows (The Pathfinders #2)       5
Historical Fiction                                                             Mrs. Houdini       5
Historical Fiction                                                    The Passion of Dolssa       5
Historical Fiction                                                   Voyager (Outlander #3)       5
Historical Fiction                                                             The Red Tent       5
Historical Fiction                                                   Between Shades of Gray       5
Historical Fiction                                                      While You Were Mine       5
Historical Fiction                        A Spy's Devotion (The Regency Spies of London #1)       5
Historical Fiction                                                The Marriage of Opposites       4
Historical Fiction                                                        A Paris Apartment       4
Historical Fiction                          World Without End (The Pillars of the Earth #2)       4
Historical Fiction                                                    Lost Among the Living       4
           Mystery                                   A Time of Torment (Charlie Parker #14)       5
           Mystery        What Happened on Beale Street (Secrets of the South Mysteries #2)       5
           Mystery The Bachelor Girl's Guide to Murder (Herringford and Watts Mysteries #1)       5
           Mystery                                        The Silkworm (Cormoran Strike #2)       5
           Mystery                                                        The Girl You Lost       5
           Mystery                                                            Sharp Objects       4
           Mystery                                                      The Past Never Ends       4
           Mystery                          The Murder of Roger Ackroyd (Hercule Poirot #4)       4
           Mystery                    Murder at the 42nd Street Library (Raymond Ambler #1)       4
           Mystery                         Delivering the Truth (Quaker Midwife Mystery #1)       4
           Mystery                      The Mysterious Affair at Styles (Hercule Poirot #1)       4
           Mystery   The No. 1 Ladies' Detective Agency (No. 1 Ladies' Detective Agency #1)       4
            Travel                                       1,000 Places to See Before You Die       5
            Travel         Full Moon over Noah’s Ark: An Odyssey to Mount Ararat and Beyond       4
            Travel                                         A Year in Provence (Provence #1)       4
```

## pd.read_sql vs pd.merge cross-check (JOIN query, no SQL for the merge side)

**pd.read_sql result:**

```
     category_name                                                                    title  rating
Historical Fiction                                  A Flight of Arrows (The Pathfinders #2)       5
Historical Fiction                                                             Mrs. Houdini       5
Historical Fiction                                                    The Passion of Dolssa       5
Historical Fiction                                                   Voyager (Outlander #3)       5
Historical Fiction                                                             The Red Tent       5
Historical Fiction                                                   Between Shades of Gray       5
Historical Fiction                                                      While You Were Mine       5
Historical Fiction                        A Spy's Devotion (The Regency Spies of London #1)       5
Historical Fiction                                                The Marriage of Opposites       4
Historical Fiction                                                        A Paris Apartment       4
Historical Fiction                          World Without End (The Pillars of the Earth #2)       4
Historical Fiction                                                    Lost Among the Living       4
           Mystery                                   A Time of Torment (Charlie Parker #14)       5
           Mystery        What Happened on Beale Street (Secrets of the South Mysteries #2)       5
           Mystery The Bachelor Girl's Guide to Murder (Herringford and Watts Mysteries #1)       5
           Mystery                                        The Silkworm (Cormoran Strike #2)       5
           Mystery                                                        The Girl You Lost       5
           Mystery                                                            Sharp Objects       4
           Mystery                                                      The Past Never Ends       4
           Mystery                          The Murder of Roger Ackroyd (Hercule Poirot #4)       4
           Mystery                    Murder at the 42nd Street Library (Raymond Ambler #1)       4
           Mystery                         Delivering the Truth (Quaker Midwife Mystery #1)       4
           Mystery                      The Mysterious Affair at Styles (Hercule Poirot #1)       4
           Mystery   The No. 1 Ladies' Detective Agency (No. 1 Ladies' Detective Agency #1)       4
            Travel                                       1,000 Places to See Before You Die       5
            Travel         Full Moon over Noah’s Ark: An Odyssey to Mount Ararat and Beyond       4
            Travel                                         A Year in Provence (Provence #1)       4
```

**pd.merge result:**

```
     category_name                                                                    title  rating
Historical Fiction                                  A Flight of Arrows (The Pathfinders #2)       5
Historical Fiction                                                             Mrs. Houdini       5
Historical Fiction                                                    The Passion of Dolssa       5
Historical Fiction                                                   Voyager (Outlander #3)       5
Historical Fiction                                                             The Red Tent       5
Historical Fiction                                                   Between Shades of Gray       5
Historical Fiction                                                      While You Were Mine       5
Historical Fiction                        A Spy's Devotion (The Regency Spies of London #1)       5
Historical Fiction                                                The Marriage of Opposites       4
Historical Fiction                                                        A Paris Apartment       4
Historical Fiction                          World Without End (The Pillars of the Earth #2)       4
Historical Fiction                                                    Lost Among the Living       4
           Mystery                                   A Time of Torment (Charlie Parker #14)       5
           Mystery        What Happened on Beale Street (Secrets of the South Mysteries #2)       5
           Mystery The Bachelor Girl's Guide to Murder (Herringford and Watts Mysteries #1)       5
           Mystery                                        The Silkworm (Cormoran Strike #2)       5
           Mystery                                                        The Girl You Lost       5
           Mystery                                                            Sharp Objects       4
           Mystery                                                      The Past Never Ends       4
           Mystery                          The Murder of Roger Ackroyd (Hercule Poirot #4)       4
           Mystery                    Murder at the 42nd Street Library (Raymond Ambler #1)       4
           Mystery                         Delivering the Truth (Quaker Midwife Mystery #1)       4
           Mystery                      The Mysterious Affair at Styles (Hercule Poirot #1)       4
           Mystery   The No. 1 Ladies' Detective Agency (No. 1 Ladies' Detective Agency #1)       4
            Travel                                       1,000 Places to See Before You Die       5
            Travel         Full Moon over Noah’s Ark: An Odyssey to Mount Ararat and Beyond       4
            Travel                                         A Year in Provence (Provence #1)       4
```


**Outputs match: True**
