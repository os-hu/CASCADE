from setuptools import setup
setup(name='CASCADE',
      entry_points={
          'console_scripts': [
              'CASCADE = cascade.CLI:main',
          ],
      },
      install_requires=[
          'tqdm',
          'openai',
          'docker',
          'tiktoken'
      ],
      include_package_data=True
)