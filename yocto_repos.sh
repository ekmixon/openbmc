branches=(
    rocko
    zeus
    lf-master
    lf-dunfell
    lf-gatesgarth
    lf-hardknott
)

rocko_repos=(
    meta-openembedded:eae996301
    meta-security:74860b2
    poky:5f660914cd # bitbake: bitbake-user-manual: Fixed section head typo
)
warrior_repos=(
    meta-openembedded:a24acf94d
    meta-security:4f7be0d
    poky:d865ce7154 # python3: Upgrade 3.7.4 -> 3.7.5
)
zeus_repos=(
    meta-openembedded:2b5dd1eb8
    meta-security:52e83e6
    poky:d88d62c20d # selftest/signing: Ensure build path relocation is safe
)
lf_master_repos=(
    lf-openbmc:b45a0d171
)
lf_dunfell_repos=(
    lf-openbmc:9add46f3d
)
lf_gatesgarth_repos=(
    lf-openbmc:18c6a7704
)
lf_hardknott_repos=(
    lf-openbmc:d7eca3aac
)
